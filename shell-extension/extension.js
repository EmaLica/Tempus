import GObject from 'gi://GObject';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Clutter from 'gi://Clutter';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const BUS_NAME = 'io.github.EmaLica.Tempus';
const OBJECT_PATH = '/io/github/EmaLica/Tempus/Timer';
const DESKTOP_ID = 'io.github.EmaLica.Tempus.desktop';

const IFACE = `
<node>
  <interface name="io.github.EmaLica.Tempus.Timer">
    <method name="Toggle"/>
    <method name="Reset"/>
    <method name="Skip"/>
    <method name="SetSessionType"><arg type="s" name="session" direction="in"/></method>
    <method name="Present"/>
    <property name="State" type="s" access="read"/>
    <property name="SessionType" type="s" access="read"/>
    <property name="SessionName" type="s" access="read"/>
    <property name="TimeLabel" type="s" access="read"/>
    <property name="Running" type="b" access="read"/>
  </interface>
</node>`;

const TimerProxy = Gio.DBusProxy.makeProxyWrapper(IFACE);

// stessi colori del ring nell'app (SESSION_COLORS in window.py)
const SESSION_COLOR = {
    'focus': '#d82b2b',
    'short-break': '#2eb764',
    'long-break': '#3485e4',
    'custom': '#9c4fd4',
};
const OFF_COLOR = 'rgba(255,255,255,0.45)';

const SESSIONS = [
    ['focus', 'Focus'],
    ['short-break', 'Short Break'],
    ['long-break', 'Long Break'],
    ['custom', 'Custom'],
];

const Indicator = GObject.registerClass(
class Indicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Tempus');

        const box = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        this._dot = new St.Widget({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tempus-dot',
        });
        this._label = new St.Label({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tempus-panel-label',
        });
        this._label.visible = false;
        box.add_child(this._dot);
        box.add_child(this._label);
        this.add_child(box);

        this._buildMenu();

        this._proxy = null;
        this._propsId = 0;
        this._destroyed = false;
        this._watchId = Gio.bus_watch_name(
            Gio.BusType.SESSION, BUS_NAME,
            Gio.BusNameWatcherFlags.NONE,
            () => this._onAppeared(),
            () => this._onVanished(),
        );

        this._sync();
    }

    _buildMenu() {
        this._timeItem = new PopupMenu.PopupMenuItem('Tempus', {reactive: false});
        this.menu.addMenuItem(this._timeItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._toggleItem = new PopupMenu.PopupMenuItem('Start');
        this._toggleItem.connect('activate', () => this._call('Toggle'));
        this.menu.addMenuItem(this._toggleItem);

        this._resetItem = new PopupMenu.PopupMenuItem('Reset');
        this._resetItem.connect('activate', () => this._call('Reset'));
        this.menu.addMenuItem(this._resetItem);

        this._skipItem = new PopupMenu.PopupMenuItem('Skip');
        this._skipItem.connect('activate', () => this._call('Skip'));
        this.menu.addMenuItem(this._skipItem);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._sessionItems = [];
        for (const [id, label] of SESSIONS) {
            const item = new PopupMenu.PopupMenuItem(label);
            item.connect('activate', () => {
                if (this._proxy)
                    this._proxy.SetSessionTypeRemote(id, () => {});
            });
            this.menu.addMenuItem(item);
            this._sessionItems.push([id, item]);
        }

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._openItem = new PopupMenu.PopupMenuItem('Open Tempus');
        this._openItem.connect('activate', () => this._open());
        this.menu.addMenuItem(this._openItem);
    }

    _onAppeared() {
        if (this._proxy)
            return;
        new TimerProxy(Gio.DBus.session, BUS_NAME, OBJECT_PATH, (proxy, err) => {
            if (this._destroyed)
                return;
            if (err) {
                this._proxy = null;
                this._sync();
                return;
            }
            this._proxy = proxy;
            this._propsId = proxy.connect('g-properties-changed', () => this._sync());
            this._sync();
        });
    }

    _onVanished() {
        if (this._proxy && this._propsId) {
            this._proxy.disconnect(this._propsId);
            this._propsId = 0;
        }
        this._proxy = null;
        this._sync();
    }

    _call(method) {
        if (this._proxy)
            this._proxy[`${method}Remote`](() => {});
    }

    _open() {
        if (this._proxy) {
            this._proxy.PresentRemote(() => {});
            return;
        }
        const app = Gio.DesktopAppInfo.new(DESKTOP_ID);
        if (app)
            app.launch([], null);
    }

    _sync() {
        const p = this._proxy;
        const state = p ? p.State : null;
        const stype = p ? p.SessionType : 'focus';
        const active = state === 'running' || state === 'paused';
        const color = SESSION_COLOR[stype] || SESSION_COLOR['focus'];

        if (p && active) {
            this._dot.style = `background-color: ${color};`;
            this._label.text = p.TimeLabel;
            this._label.visible = true;
            this.opacity = 255;
        } else if (p) {
            this._dot.style = `border: 2px solid ${color}; background-color: transparent;`;
            this._label.text = p.SessionName;
            this._label.visible = true;
            this.opacity = 255;
        } else {
            this._dot.style = `border: 2px solid ${OFF_COLOR}; background-color: transparent;`;
            this._label.visible = false;
            this.opacity = 160;
        }

        let toggle = 'Start';
        if (state === 'running')
            toggle = 'Pause';
        else if (state === 'paused')
            toggle = 'Resume';
        this._toggleItem.label.text = toggle;

        this._toggleItem.setSensitive(!!p);
        this._resetItem.setSensitive(!!p);
        this._skipItem.setSensitive(!!p);

        for (const [id, item] of this._sessionItems) {
            item.setSensitive(!!p);
            item.setOrnament(p && stype === id
                ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
        }

        this._timeItem.label.text = p
            ? `${p.SessionName} · ${p.TimeLabel}` : 'Tempus not running';
    }

    destroy() {
        this._destroyed = true;
        if (this._watchId) {
            Gio.bus_unwatch_name(this._watchId);
            this._watchId = 0;
        }
        if (this._proxy && this._propsId) {
            this._proxy.disconnect(this._propsId);
            this._propsId = 0;
        }
        this._proxy = null;
        super.destroy();
    }
});

export default class TempusExtension extends Extension {
    enable() {
        this._indicator = new Indicator();
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
