SUBJECT_COLORS = [
    "#3584e4",
    "#1c9c8b",
    "#c64600",
    "#9141ac",
    "#e5a50a",
    "#865e3c",
]


def default_color(index: int) -> str:
    return SUBJECT_COLORS[index % len(SUBJECT_COLORS)]
