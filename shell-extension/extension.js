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
        this._icon = new St.Icon({
            icon_name: 'alarm-symbolic',
            style_class: 'system-status-icon',
        });
        this._label = new St.Label({
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'tempus-panel-label',
        });
        this._label.visible = false;
        box.add_child(this._icon);
        box.add_child(this._label);
        this.add_child(box);

        this._buildMenu();

        this._proxy = null;
        this._propsId = 0;
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

        this._sessionSub = new PopupMenu.PopupSubMenuMenuItem('Session');
        for (const [id, label] of SESSIONS) {
            const item = new PopupMenu.PopupMenuItem(label);
            item.connect('activate', () => {
                if (this._proxy)
                    this._proxy.SetSessionTypeRemote(id, () => {});
            });
            this._sessionSub.menu.addMenuItem(item);
        }
        this.menu.addMenuItem(this._sessionSub);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        this._openItem = new PopupMenu.PopupMenuItem('Open Tempus');
        this._openItem.connect('activate', () => this._open());
        this.menu.addMenuItem(this._openItem);
    }

    _onAppeared() {
        this._proxy = new TimerProxy(Gio.DBus.session, BUS_NAME, OBJECT_PATH,
            (proxy, err) => {
                if (err) {
                    this._proxy = null;
                    this._sync();
                    return;
                }
                this._propsId = this._proxy.connect(
                    'g-properties-changed', () => this._sync());
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
        if (!this._proxy)
            return;
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
        const running = this._proxy ? this._proxy.Running : false;
        const state = this._proxy ? this._proxy.State : null;
        const active = state === 'running' || state === 'paused';

        this.reactive = true;
        this._icon.opacity = this._proxy ? 255 : 130;

        if (this._proxy && active) {
            this._label.text = `${this._proxy.TimeLabel} · ${this._proxy.SessionName}`;
            this._label.visible = true;
        } else {
            this._label.visible = false;
        }

        const on = this._proxy !== null;
        this._toggleItem.label.text = running ? 'Pause' : 'Start';
        this._toggleItem.setSensitive(on);
        this._resetItem.setSensitive(on);
        this._skipItem.setSensitive(on);
        this._sessionSub.setSensitive(on);

        if (this._proxy)
            this._timeItem.label.text = `${this._proxy.SessionName} · ${this._proxy.TimeLabel}`;
        else
            this._timeItem.label.text = 'Tempus not running';
    }

    destroy() {
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
