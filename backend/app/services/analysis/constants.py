"""Fixed vocabulary: placental preparations, heart structures, use cases, and target resolution."""

PLACENTA_PREPS: dict[str, list[str]] = {
    "Amnion_decell": ["Amnion_decell_1", "Amnion_decell_2", "Amnion_decell_3", "Amnion_decell_4"],
    "Amnion_native": ["Amnion_native_1", "Amnion_native_2"],
    "Basaltissue_decell": ["Basaltissue_decell_1", "Basaltissue_decell_2", "Basaltissue_decell_3"],
    "Basaltissue_native": ["Basaltissue_native_1", "Basaltissue_native_2"],
    "Chorion_decell": ["Chorion_decell_1", "Chorion_decell_2", "Chorion_decell_3", "Chorion_decell_4"],
    "Chorion_native": ["Chorion_native_1", "Chorion_native_2"],
    "UmbilicalCord_decell": [
        "UmbilicalCord_decell_1",
        "UmbilicalCord_decell_2",
        "UmbilicalCord_decell_3",
        "UmbilicalCord_decell_4",
    ],
    "UmbilicalCord_native": ["UmbilicalCord_native_1"],
}

HEART_REGIONS: list[str] = [
    "largeAtery",
    "coronaryArtery",
    "Atrium",
    "Ventricle",
    "AV-Valves",
    "SL-Valves",
]

REPLICATE_TO_PREP: dict[str, str] = {
    replicate: prep for prep, replicates in PLACENTA_PREPS.items() for replicate in replicates
}

USE_CASE: dict[str, str] = {
    "largeAtery": "great-vessel / arterial graft",
    "coronaryArtery": "coronary conduit",
    "Atrium": "atrial patch",
    "Ventricle": "myocardial patch (ventricular wall)",
    "AV-Valves": "atrioventricular valve repair",
    "SL-Valves": "semilunar (aortic/pulmonary) valve replacement",
}

_STRUCTURE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("semilunar", "aortic valve", "pulmonary valve", "sl-valve", "sl valve"), "SL-Valves"),
    (("atrioventricular", "mitral", "tricuspid", "av-valve", "av valve"), "AV-Valves"),
    (("coronary",), "coronaryArtery"),
    (("ventric", "myocard"), "Ventricle"),
    (("atrium", "atrial"), "Atrium"),
    (("large artery", "large atery", "great vessel", "aorta", "arterial graft"), "largeAtery"),
]


def match_structure(*texts: str | None) -> str | None:
    """Resolve free-text target fields to a heart structure, or None if unclear."""
    haystack = " ".join(t for t in texts if t).lower()
    for keywords, region in _STRUCTURE_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return region
    return None
