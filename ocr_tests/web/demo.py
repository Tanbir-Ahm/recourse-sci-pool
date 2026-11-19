"""The demo and the test double of the Reading Desk site: invented pages and invented readings, no model, no cost.

make_pages() draws three plain page images. Each carries its number in the colour of its centre pixel (the padded second view keeps the centre), so the stub reader knows which page it was given.
reading() returns what a reader would say about that page, with the features the site shows: two readings that disagree on a date, a struck-out word and the word written above it, a doubtful reading,
a sentence that does not make sense, a stamp over text, an unclear word. Everything said here is INVENTED for the demo; none of it is a reading of a real page.
"""
import io, os

SIZE = (700, 990)
MAGIC = 0xA7
DEMO_NAME = "Demo complaint (invented text)"

PAGES = {
    1: {"orig": ["১. ফৰিয়াদী %(date)s তাৰিখে থানাত জনালে", "২. আসামীয়ে দাগ নং 52 ৰ মাটিত সোমাই গছ কাটিলে", "৩. জামাবন্দী অনুসৰি মাটি 2 বিঘা 1 কঠা 8 লেছা"],
        "en": "Complaint. On %(date)s the complainant told the police station that the accused had entered the land at Dag No. 52 and cut trees. According to the jamabandi the land measures 2 Bigha 1 Katha 8 Lessa.",
        "dates": ("14/3/2024", "11/3/2024", "14/3/2024")},
    2: {"orig": ["৪. %(strike)s ক থানালৈ লৈ গ'ল", "৫. তেওঁ লিখিতভাৱে ফৰিয়াদ দিলে", "৬. 50,000/- (পঞ্চাশ হাজাৰ টকা মাত্ৰ) দিব লাগিব"]},
    3: {"orig": ["৭. %(stamp)s", "৮. তাৰিখ 18/4/2024", "৯. ন্যায়িক হাকিম প্ৰথম শ্ৰেণী"]},
}
ENG2_1 = ("The %(strike_en)s was taken to the police station. He gave a %(doubt)s in writing. "
          "He said that he would to the matter in order to return of the fence. The amount of 50,000/- (fifty thousand rupees only) was to be paid.")
ENG2_2 = ("The witness was taken to the police station. He gave a complaint in writing. "
          "He said that he would settle the matter in order to return the fence. The amount of 50,000/- (fifty thousand rupees only) was to be paid.")
ENG3_1 = "The accused said the money would be paid after [unclear] days. [stamp over text] Endorsed on 18/4/2024. Judicial Magistrate, 1st Class."
ENG3_2 = "Endorsed on 18/4/2024 before the Judicial Magistrate. The matter was adjourned and the parties were told to appear again."
SENSE_QUOTE = "He said that he would to the matter in order to return of the fence."


def make_pages(dest):
    """Three PNG pages in dest, named demo_p1.png .. demo_p3.png (so the pipeline joins them as one document). Returns the paths."""
    from PIL import Image, ImageDraw
    os.makedirs(dest, exist_ok=True)
    out = []
    for n in (1, 2, 3):
        im = Image.new("RGB", SIZE, (251, 250, 246))
        d = ImageDraw.Draw(im)
        for y in range(120, SIZE[1] - 80, 34):
            d.line([(70, y), (SIZE[0] - 70, y)], fill=(201, 204, 209), width=1)
        d.text((70, 60), "DEMO PAGE %d OF 3" % n, fill=(60, 70, 80))
        d.text((70, 82), "Invented text. No model reads this image.", fill=(120, 128, 138))
        im.putpixel((SIZE[0] // 2, SIZE[1] // 2), (n, MAGIC, 0))
        p = os.path.join(dest, "demo_p%d.png" % n)
        im.save(p)
        out.append(p)
    return out


def page_number(image_bytes):
    """Which demo page this image is (from the centre pixel, which survives padding), or None for any other image."""
    from PIL import Image
    im = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    r, g, _ = im.getpixel((im.width // 2, im.height // 2))
    return r if g == MAGIC and r in (1, 2, 3) else None


def reading(image_bytes, marked, ultra):
    """The reply of the stub reader: 'TRANSCRIPTION ... TRANSLATION ...'. view 1 is the image as given, view 2 the padded copy (a larger image), the ultra-high look the same size as view 1."""
    from PIL import Image
    n = page_number(image_bytes) or 1
    im = Image.open(io.BytesIO(image_bytes))
    view2 = im.size != SIZE and not ultra
    if n == 1:
        a, b, c = PAGES[1]["dates"]
        date = c if ultra else (b if view2 else a)
        orig = "\n".join(PAGES[1]["orig"]) % {"date": date}
        eng = PAGES[1]["en"] % {"date": date}
        if view2:
            eng = eng.replace("cut trees", "cut four trees")
    elif n == 2:
        if marked and not view2 and not ultra:
            orig = "\n".join(PAGES[2]["orig"]) % {"strike": "~~ভুক্তভোগী~~ ^সাক্ষী^"}
            eng = ENG2_1 % {"strike_en": "~~victim~~ ^witness^", "doubt": "<doubtful: written 'complaint', likely meant 'compliant'>"}
        else:
            orig = "\n".join(PAGES[2]["orig"]) % {"strike": "সাক্ষী"}
            eng = ENG2_2
    else:
        if view2:
            orig = "\n".join(["৭. তাৰিখ 18/4/2024", "৮. হাকিমৰ আগত পুনৰ উপস্থিত হ'বলৈ কোৱা হ'ল"])
            eng = ENG3_2
        else:
            orig = "\n".join(PAGES[3]["orig"]) % {"stamp": "[stamp over text]"}
            eng = ENG3_1
    if not marked:
        eng = eng.replace("~~victim~~ ^witness^", "witness")
        orig = orig.replace("~~ভুক্তভোগী~~ ^সাক্ষী^", "সাক্ষী")
    return "TRANSCRIPTION\n%s\nTRANSLATION\n%s" % (orig, eng)
