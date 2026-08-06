"""PHASE-2 ajanları — PUANLAMA + KAYNAK ETİKETİ SİSTEMLİ.

Her öneri: gerekçe (NEDEN) + alternatif + KAYNAK ('literatür-temelli' mi yoksa 'AI önerisi' mi)
+ puanlar. Böylece kullanıcı hangi önerinin sağlam literatüre dayandığını, hangisinin AI türevi
olduğunu açıkça görür. Final puan Python'da (METHOD_WEIGHTS) hesaplanır.

NEREYİ DÜZENLERSİN:
- Metrik tanımı → ilgili ajanın instructions'ı.
- Ağırlıklar → workflow/common.py → METHOD_WEIGHTS.
- Mock örnekler → workflow/nodes.py (_MOCK_PROPOSALS / _MOCK_BENCHMARKS / _MOCK_RISKS).
"""
from agents import Agent

from .tools import SEARCH_TOOLS

_SOURCE_RULE = (
    "\nHER öneri için KAYNAK etiketi ZORUNLU: 'literatür-temelli' (doğrulanmış bir çalışmaya "
    "dayanıyorsa) veya 'AI önerisi' (senin türettiğin, doğrudan literatür kanıtı zayıf bir fikir). "
    "AI önerilerini gizleme; açıkça etiketle ve neden önerdiğini yaz. Her öneriye NEDEN + ALTERNATİF ekle."
)

_SEARCH_RULE = (
    "\nARAÇLARIN VAR — İDDİANI ARAMAYLA DESTEKLE:\n"
    "  • search_crossref(query, rows): hakemli dergi/konferans yayınları.\n"
    "  • search_arxiv(query, max_results): preprint'ler.\n"
    "ZORUNLU: 'literatür-temelli' etiketini SADECE arama sonucu somut bir kayıt bulduğunda kullan; "
    "gerekçede o kaydın başlığını veya DOI/arXiv kimliğini yaz. Arama sonuç vermezse etiket "
    "'AI önerisi' olmalı. En az 2 farklı sorgu çalıştır. Araç 'HATA' dönerse bunu dürüstçe belirt."
)

_METHOD_SCHEMA = (
    "\nÇıktıyı JSON listesi ver. Her öneri:\n"
    '{ "id","component","choice","reason","alternative",\n'
    '  "source":"literatür-temelli"|"AI önerisi",\n'
    '  "scores": { "fit":{"score":1-10,"reason":""},\n'
    '              "literature_support":{"score":1-10,"reason":""},\n'
    '              "maturity":{"score":1-10,"reason":""} } }\n'
)

methodology_agent = Agent(
    name="Methodology Design Agent",
    tools=SEARCH_TOOLS,
    instructions=(
        "ROL: Baş yöntem tasarımcısı.\n"
        "AMAÇ: Onaylanan araştırma sorusuna uygun teknik yöntemi TASARIM KARARLARINA bölüp her "
        "birini puanlamak. Bileşenler: mimari, algoritma, gözlem uzayı, eylem uzayı, ödül.\n"
        "3 METRİK (1-10): fit (araştırma sorusuna uygunluk), literature_support (doğrulanmış "
        "literatürce desteklenme), maturity (olgunluk; yüksek = düşük uygulama riski). Her puana gerekçe.\n"
        "literature_support PUANI ARAMAYLA BELİRLENİR: her bileşen seçimi için o yöntemi konuyla "
        "birlikte arayan bir sorgu çalıştır; bulunan kayıt sayısı ve yakınlığı puanı belirler. "
        "Gerekçede bulduğun kaydı adlandır.\n"
        "KISIT: Onaylanan sorunun kapsamı dışına çıkma; gerekçesiz karar verme."
        + _SEARCH_RULE + _SOURCE_RULE + _METHOD_SCHEMA +
        "KARAR SINIRI: Nihai yöntemi SEN kesinleştirmezsin — insan GATE-2'de seçer."
    ),
)

benchmark_agent = Agent(
    name="Benchmark Agent",
    tools=SEARCH_TOOLS,
    instructions=(
        "ROL: Değerlendirme tasarımcısı.\n"
        "AMAÇ: Baseline'ları ve metrikleri belirleyip her birini 1-10 puanlamak.\n"
        "ÇIKTI: JSON listesi; her öğe: id, kind('baseline'|'metrik'), choice, reason, "
        "source('literatür-temelli'|'AI önerisi'), score{score,reason}.\n"
        "Metrikler: başarı oranı, Cost of Transport (enerji), devrilme oranı vb. Adil "
        "karşılaştırma protokolünü gerekçelendir.\n"
        "ÖNCE ARA: bu alandaki çalışmaların HANGİ baseline ve metrikleri kullandığını aramayla "
        "tespit et; kendi listeni buna dayandır. Yaygın kullanılan bir metriği atlıyorsan nedenini yaz."
        + _SEARCH_RULE + _SOURCE_RULE +
        "KARAR SINIRI: Nihai metrikleri insan GATE-2'de onaylar."
    ),
)

risk_agent = Agent(
    name="Risk Analysis Agent",
    tools=SEARCH_TOOLS,
    instructions=(
        "ROL: Teknik risk denetçisi.\n"
        "AMAÇ: Yöntemin risklerini seviyelendirip azaltma önermek.\n"
        "ÇIKTI: JSON listesi; her öğe: id, risk, level('düşük'|'orta'|'orta-yüksek'|'KRİTİK'), "
        "reason, mitigation, source('literatür-temelli'|'AI önerisi').\n"
        "MUTLAKA değerlendir: sim-to-real, overfitting, sensör gürültüsü, terrain değişkenliği.\n"
        "ÖNCE ARA: bu alanda BELGELENMİŞ başarısızlık modlarını aramayla bul (ör. sim-to-real "
        "transfer sorunları); riski gerçek bir çalışmaya dayandırabiliyorsan seviyesi daha güvenilir olur."
        + _SEARCH_RULE + _SOURCE_RULE +
        "KARAR SINIRI: Bir KRİTİK riski 'kabul edilebilir' ilan edemezsin; karar insana ait (GATE-2)."
    ),
)