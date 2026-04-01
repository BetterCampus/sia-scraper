use scraper::Selector;

const SELECTORS: &[(&str, &str)] = &[
    ("H2_SELECTOR", "h2"),
    ("CREDITS_SELECTOR", "span.detass-creditos"),
    ("CREDITS_SPAN_SELECTOR", "span.detass-creditos span"),
    ("TYPOLOGY_SPAN_SELECTOR", "span.detass-tipologia span"),
    ("GENERIC_SPAN_SELECTOR", "span"),
    ("LISTA_ELEMENTO_SELECTOR", "span.lista-elemento"),
    ("GROUP_TITLE_SELECTOR", "h2.af_showDetailHeader_title-text0"),
    ("PANEL_GROUP_SELECTOR", "div.af_panelGroupLayout"),
    ("DIV_SELECTOR", "div"),
    ("GROUP_CONTENT_SELECTOR", ".af_showDetailHeader_content0"),
    (
        "PREREQ_CONDITION_SELECTOR",
        "span.borde.salto.af_panelGroupLayout > div.margin-t.af_panelGroupLayout",
    ),
    ("PREREQ_STRONG_SELECTOR", "span.strong.af_panelGroupLayout"),
    (
        "PREREQ_VALUE_SIBLING_SELECTOR",
        "span.strong.af_panelGroupLayout + span",
    ),
    (
        "PREREQ_HEADER_SELECTOR",
        "span.strong.af_panelGroupLayout > span.margin-l",
    ),
    ("PREREQ_SPAN_SELECTOR", "span.af_panelGroupLayout > span"),
];

fn main() {
    for (name, selector_str) in SELECTORS {
        if let Err(e) = Selector::parse(selector_str) {
            panic!("Invalid CSS selector in registry: {name}='{selector_str}'. Error: {e:?}");
        }
    }

    println!("cargo:rerun-if-changed=build.rs");
}
