"""Testlerde kullanılan örnek (sahte) LLM çıktıları."""
from contentflow import models

IDENTITY = models.BrandIdentity(
    story="Küçük bir dükkân.", mission="İyi kahveyi erişilebilir kılmak.",
    values=[models.BrandValue(name=n, description="d") for n in ("Şeffaflık", "Topluluk", "Odak")],
    palette=[models.ColorSwatch(name=n, hex=h, usage="u") for n, h in
             (("Çekirdek", "#3B2A20"), ("Krema", "#F4EBDD"), ("Adaçayı", "#8FA58B"), ("Turuncu", "#E07A3F"))],
    typography=models.Typography(heading_font="Fraunces", body_font="Inter", license="OFL", rationale="r"),
    visual_style=models.VisualStyle(style="s", lighting="l", composition="c", color_usage="cu",
                                    forbidden=["yazı yok", "logo yok"]),
)

COMPETITORS = models.CompetitorAnalysis(
    competitors=[models.Competitor(name=f"R{i}", type="t", positioning="p", strengths=["a"], weaknesses=["b"],
                                   our_difference="f", verified=(i == 0)) for i in range(3)],
    market_note="not",
)

PERSONAS = models.PersonaSet(personas=[models.Persona(
    name="Ece", age=21, occupation="Öğrenci", location="Kampüs", daily_routine="r", coffee_habit="c",
    pain_points=["p1"], motivations=["m1"],
    channel_habits=[models.ChannelHabit(channel="Instagram", habit="akşam")], quote="q")])

VOICE = models.BrandVoice(
    personality=[models.AdjectiveRule(adjective=a, meaning="m") for a in ("samimi", "sakin", "meraklı")],
    we_are_table=[models.WeAreRow(we_are="samimi", we_are_not="laubali")],
    words_to_use=["demlemek"], words_to_avoid=["eşsiz"], address_rule="sen", emoji_rule="az",
    good_examples=["İyi."], bad_examples=[models.BadExample(sentence="Kötü!!!", why_bad="abartı")],
    tts_tone="Sıcak ve sakin.", tts_rate_percent=-5, tts_pitch_hz=0,
)

STRATEGY = models.ContentStrategy(
    frame=models.StrategyFrame(why="w", who="w", what="w", how="h"),
    pillars=[models.ContentPillar(name=f"S{i}", purpose="p", description="d", persona_match="m",
                                  example_topics=["t"], best_channels=["Instagram"]) for i in range(3)],
)


def _row(day, deliv, pillar, topic):
    return models.CalendarItemDraft(
        day=day, time_slot="09:00", channel="Instagram", format="Gönderi", deliverables=deliv,
        pillar=pillar, persona="Ece", topic=topic, goal="etkileşim",
        rationale=f"Ece sabah derse giderken bakıyor; {pillar} sütunu bu ihtiyaca hitap ediyor.")


CALENDAR = models.CalendarDraft(items=[
    _row(1, ["blog"], "S0", "Blog"),
    _row(2, ["social_post", "image"], "S1", "Gönderi 1"),
    _row(3, ["social_post", "image"], "S2", "Gönderi 2"),
    _row(4, ["video", "voiceover"], "S0", "Video"),
    _row(5, ["social_post", "image"], "S1", "Gönderi 3"),
    _row(6, ["social_post"], "S2", "Ek"),
    _row(7, ["social_post"], "S0", "Kapanış"),
], strategy_note="Hafta kurgusu.")

_BODY = "\n\n".join(
    f"## Başlık {h}\n\n" + " ".join(["Demleme ritüeli sakin bir odak anı yaratır ve günü yumuşatır."] * 29)
    for h in range(4)
)
BLOG = models.BlogPost(
    title_h1="Deadline gecesi için filtre kahve rehberi", meta_description="Filtre kahve ile deadline gecesi rehberi.",
    slug="deadline-gecesi-filtre-kahve", focus_keyword="filtre kahve",
    secondary_keywords=["demleme", "çekirdek", "öğütme"], body_markdown=_BODY, cta="Uğra.", flagged_claims=[],
)

SOCIAL = models.SocialPost(
    channel="Instagram", hook="Hook.", body="Metin.", hashtags=["#demlikco", "#kahve", "#odak"], cta="Gel.",
    image_description="Ahşap masada fincan.", alt_text="Ahşap masada fincan.",
)

IMAGE_PROMPT = models.ImagePrompt(
    prompt_en=" ".join(["A ceramic cup of filter coffee on a wooden desk near a window,"] * 6),
    description_tr="Masada kahve.", palette_hexes=["#3B2A20", "#F4EBDD"],
)

VOICEOVER = models.VoiceoverScript(text=" ".join(["Deadline gecesi sakin bir köşe ve iyi kahve seni bekliyor."] * 5),
                                   pronunciation_notes=[])
VIDEO_SCRIPT = models.VideoScript(scenes=[models.VideoScene(visual_description="Masa", on_screen_text=f"Sahne {i}",
                                                            duration_s=4) for i in range(4)],
                                  closing_text="Ders arasında da iyi kahve.")
_F = models.ReviewField
REVIEW_RISKY = models.ReviewReport(
    ton_tutarliligi=_F(durum="uygun", aciklama="Uyumlu.", oneri=""),
    anahtar_kelime=_F(durum="uygun", aciklama="Odaklı.", oneri=""),
    telif_kontrolu=_F(durum="uygun", aciklama="Sorun yok.", oneri=""),
    kaynak_dogrulama=models.SourceCheck(durum="riskli", aciklama="Bir iddia var.", oneri="Kaynak ekle.",
                                        isaretlenen_iddialar=["%73 öğrenci"]))
