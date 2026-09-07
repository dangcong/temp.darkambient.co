from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AURORA_TEAL = {
    "50": "#f0fdfa",
    "100": "#ccfbf1",
    "200": "#99f6e4",
    "300": "#5eead4",
    "400": "#2dd4bf",
    "500": "#0f766e",
    "600": "#115e59",
    "700": "#134e4a",
    "800": "#0f3d3a",
    "900": "#082f2d",
}

OLD_BRAND_ORANGE = (
    "#fff7f5",
    "#fff0eb",
    "#ffd9cc",
    "#ffb8a3",
    "#ff8c6b",
    "#ff5528",
    "#e64a20",
    "#cc3f18",
    "#a33010",
    "#7a2008",
)


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_active_surfaces_use_darkambient_brand():
    index_html = read("index.html")
    user_html = read("user.html")
    app_js = read("app.js")

    assert "DarkAmbient Admin" in index_html
    assert "DarkAmbient Inbox" in user_html
    assert 'Dark<span class="text-lush-500">Ambient</span>' in index_html
    assert "DarkAmbient" in user_html
    assert "logo.svg?v=20260907-mail-capabilities" in index_html
    assert "logo.svg?v=20260721-aurora-teal" in user_html
    assert "from_email || 'DarkAmbient'" in app_js
    assert "LushMail" not in index_html
    assert "LushMail" not in user_html
    assert "from_email || 'LushMail'" not in app_js


def test_active_surfaces_have_no_legacy_alias_or_mojibake():
    active_text = "\n".join(read(name) for name in ("index.html", "user.html", "app.js", "user.js"))

    assert "lush@" not in active_text.lower()
    for broken_sequence in ("Ã", "Ä", "Â", "á»"):
        assert broken_sequence not in active_text


def test_logo_is_accessible_darkambient_monogram():
    logo = read("logo.svg")

    assert "DarkAmbient Logo" in logo
    assert "DA monogram" in logo
    assert "teal" in logo
    assert "#0f766e" in logo.lower()
    assert "#ff5528" not in logo.lower()


def test_active_surfaces_use_aurora_teal_theme():
    index_html = read("index.html").lower()
    user_html = read("user.html").lower()

    for shade, value in AURORA_TEAL.items():
        assert f"{shade}: '{value}'" in index_html
        assert f"{shade}: '{value}'" in user_html

    assert "style.css?v=20260907-mail-capabilities" in index_html
    assert "user.css?v=20260721-aurora-teal" in user_html


def test_brand_orange_is_removed_from_active_assets():
    active_assets = "\n".join(
        read(name).lower()
        for name in (
            "index.html",
            "user.html",
            "style.css",
            "user.css",
            "app.js",
            "user.js",
            "logo.svg",
        )
    )

    for old_value in OLD_BRAND_ORANGE:
        assert old_value not in active_assets


def test_runtime_defaults_use_darkambient_identity():
    config = read("backend/app/config.py")
    main = read("backend/app/main.py")
    translator = read("backend/app/translator.py")
    env_example = read("deploy/darkambient/app.env.example")

    assert 'os.getenv("TEMPMAIL_PUBLIC_DOMAIN", "temp.darkambient.co")' in config
    assert 'os.getenv("TEMPMAIL_MAIL_DOMAIN", "temp.darkambient.co")' in config
    assert 'os.getenv("IMAP_HOST", "mx.temp.darkambient.co")' in config
    assert 'os.getenv("SMTP_FROM_NAME", "DarkAmbient")' in config
    assert 'FastAPI(title="DarkAmbient Temp Mail"' in main
    assert '"User-Agent": "DarkAmbient/1.0"' in translator
    assert "SMTP_FROM_NAME=DarkAmbient" in env_example
