# Словарь для маппинга аббревиатур в полные названия
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington, D.C."
}

# Страница 1: Популярные штаты
STATES_PAGE_1 = [
    ["California", "CA"], ["Florida", "FL"], ["Georgia", "GA"],
    ["Virginia", "VA"], ["New York", "NY"], ["Maryland", "MD"],
    ["Tennessee", "TN"], ["Ohio", "OH"], ["Texas", "TX"],
    ["Oregon", "OR"], ["Pennsylvania", "PA"], ["Washington, D.C.", "DC"]
]

# Страница 2
STATES_PAGE_2 = [
    ["Alabama", "AL"], ["Alaska", "AK"], ["Arizona", "AZ"],
    ["Arkansas", "AR"], ["Colorado", "CO"], ["Connecticut", "CT"],
    ["Delaware", "DE"], ["Hawaii", "HI"], ["Idaho", "ID"],
    ["Illinois", "IL"], ["Indiana", "IN"], ["Iowa", "IA"]
]

# Страница 3
STATES_PAGE_3 = [
    ["Kansas", "KS"], ["Kentucky", "KY"], ["Louisiana", "LA"],
    ["Maine", "ME"], ["Massachusetts", "MA"], ["Michigan", "MI"],
    ["Minnesota", "MN"], ["Mississippi", "MS"], ["Missouri", "MO"],
    ["Montana", "MT"], ["Nebraska", "NE"], ["Nevada", "NV"]
]

# Страница 4
STATES_PAGE_4 = [
    ["New Hampshire", "NH"], ["New Jersey", "NJ"], ["New Mexico", "NM"],
    ["North Carolina", "NC"], ["North Dakota", "ND"], ["Oklahoma", "OK"],
    ["Rhode Island", "RI"], ["South Carolina", "SC"], ["South Dakota", "SD"],
    ["Utah", "UT"], ["Vermont", "VT"], ["Washington", "WA"],
    ["West Virginia", "WV"], ["Wisconsin", "WI"], ["Wyoming", "WY"]
]

# Все страницы для удобства
STATES_PAGES = [STATES_PAGE_1, STATES_PAGE_2, STATES_PAGE_3, STATES_PAGE_4]

# Для обратной совместимости
US_STATES_LIST = list(US_STATES.keys())
PRIORITY_STATES = [state[1] for state in STATES_PAGE_1]  # Аббревиатуры популярных штатов

