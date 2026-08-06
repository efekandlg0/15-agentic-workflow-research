"""Ajan araçları — gerçek dış kaynak sorgulama (ücretsiz, API anahtarı gerektirmez).

ARAMA (Literature Search Agent için):
- search_crossref : Crossref'te konuya göre gerçek makale arar (dergi/konferans).
- search_arxiv    : arXiv'de konuya göre gerçek preprint arar.

DOĞRULAMA (Verification Agent için):
- crossref_lookup : DOI'yi Crossref'te sorgular.
- arxiv_lookup    : arXiv ID'sini arXiv API'sinde sorgular.

NEDEN GEREKLİ: Araçsız ajan makaleleri HAFIZASINDAN uydurur — başlık makul görünür ama
DOI ya yoktur ya da sahtedir, dolayısıyla doğrulama da anlamsızlaşır. Arama aracıyla
ajan gerçek kayıtlar döndürür; doğrulama aracıyla bu kayıtlar bağımsızca teyit edilir.

NOT: İnternet gerekir. Ağ hatası durumunda araçlar 'HATA: ...' döndürür — ajan bunu
'doğrulanamadı' değil, 'kontrol edilemedi' olarak raporlamalıdır (bkz. phase1.py).
"""
import math
import re
import statistics
import time
import xml.etree.ElementTree as ET

import httpx
from agents import function_tool

_TIMEOUT = 12.0
_HTTP_RETRIES = 3
# Crossref "polite pool": iletişim bilgisi veren istemcilere daha stabil hizmet verir.
_UA = "agentic-research-starter/1.0 (mailto:research@example.com)"


def _get(url, params=None, retries=None, backoff=1.5):
    """GET + geçici hatada yeniden deneme. -> (response, None) | (None, 'HATA: ...')

    Semantic Scholar'ın anahtarsız havuzu paylaşımlı ve sıkıdır; 429 için daha uzun
    bekleme gerekir (bkz. citations_raw).
    """
    last = None
    tries = retries or _HTTP_RETRIES
    for attempt in range(tries):
        try:
            r = httpx.get(url, params=params, headers={"User-Agent": _UA},
                          timeout=_TIMEOUT, follow_redirects=True)
        except Exception as e:
            last = type(e).__name__
        else:
            if r.status_code < 500 and r.status_code != 429:
                return r, None                     # 200/404 gibi kalıcı yanıt
            last = f"HTTP {r.status_code}"
        if attempt < tries - 1:
            time.sleep(backoff * (attempt + 1))
    return None, f"HATA: sunucuya ulaşılamadı ({last})."


def lookup_doi(doi: str) -> str:
    """crossref_lookup aracının saf (test edilebilir) gövdesi."""
    d = (doi or "").strip()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d, flags=re.I).strip()
    if not d:
        return "BULUNAMADI (boş DOI)"
    r, err = _get(f"https://api.crossref.org/works/{d}")
    if err:
        return f"{err} Doğrulama yapılamadı."
    if r.status_code == 404:
        return "BULUNAMADI"
    if r.status_code != 200:
        return f"HATA: Crossref {r.status_code} döndü. Doğrulama yapılamadı."
    try:
        m = r.json()["message"]
    except Exception:
        return "HATA: Crossref yanıtı çözümlenemedi."

    title = (m.get("title") or ["(başlık yok)"])[0]
    authors = ", ".join(
        f"{a.get('family','')}".strip() for a in (m.get("author") or [])[:5]
    ) or "(yazar yok)"
    parts = (m.get("issued", {}).get("date-parts") or [[None]])[0]
    year = parts[0] if parts else None
    venue = (m.get("container-title") or [m.get("publisher", "")])
    venue = venue[0] if isinstance(venue, list) and venue else (venue or "(venue yok)")
    return f"BULUNDU | {title} | {authors} | {year} | {venue}"


def lookup_arxiv(arxiv_id: str) -> str:
    """arxiv_lookup aracının saf (test edilebilir) gövdesi."""
    a = re.sub(r"^arxiv:\s*", "", (arxiv_id or "").strip(), flags=re.I)
    a = re.sub(r"^(https?://)?arxiv\.org/abs/", "", a, flags=re.I).strip()
    if not a:
        return "BULUNAMADI (boş ID)"
    r, err = _get("https://export.arxiv.org/api/query",
                  {"id_list": a, "max_results": 1})
    if err:
        return f"{err} Doğrulama yapılamadı."
    if r.status_code != 200:
        return f"HATA: arXiv {r.status_code} döndü. Doğrulama yapılamadı."
    try:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = ET.fromstring(r.text).find("a:entry", ns)
    except Exception:
        return "HATA: arXiv yanıtı çözümlenemedi."
    if entry is None:
        return "BULUNAMADI"
    title = (entry.findtext("a:title", default="", namespaces=ns) or "").strip()
    published = (entry.findtext("a:published", default="", namespaces=ns) or "")[:10]
    authors = ", ".join(
        (e.findtext("a:name", default="", namespaces=ns) or "").strip()
        for e in entry.findall("a:author", ns)[:5]
    ) or "(yazar yok)"
    # arXiv "bulunamadı" durumunda da bazen boş başlıklı entry döner.
    if not title:
        return "BULUNAMADI"
    return f"BULUNDU | {title} | {authors} | {published}"


def _fmt_year(item: dict):
    parts = (item.get("issued", {}).get("date-parts") or [[None]])[0]
    return parts[0] if parts else None


def search_crossref_raw(query: str, rows: int = 8) -> str:
    """search_crossref aracının saf (test edilebilir) gövdesi."""
    q = (query or "").strip()
    if not q:
        return "HATA: boş sorgu."
    rows = max(1, min(int(rows or 8), 20))
    r, err = _get("https://api.crossref.org/works",
                  {"query.bibliographic": q, "rows": rows,
                   "select": "DOI,title,author,issued,container-title,is-referenced-by-count"})
    if err:
        return err
    if r.status_code != 200:
        return f"HATA: Crossref {r.status_code} döndü."
    try:
        items = r.json()["message"]["items"]
    except Exception:
        return "HATA: Crossref yanıtı çözümlenemedi."
    if not items:
        return "SONUÇ YOK"

    lines = []
    for it in items:
        title = (it.get("title") or ["(başlık yok)"])[0]
        authors = ", ".join(a.get("family", "") for a in (it.get("author") or [])[:4]) or "(yazar yok)"
        venue = (it.get("container-title") or ["(venue yok)"])
        venue = venue[0] if venue else "(venue yok)"
        lines.append(f"DOI={it.get('DOI')} | {title} | {authors} | {_fmt_year(it)} | "
                     f"{venue} | atıf≈{it.get('is-referenced-by-count', '?')}")
    return "\n".join(lines)


def search_arxiv_raw(query: str, max_results: int = 8) -> str:
    """search_arxiv aracının saf (test edilebilir) gövdesi."""
    q = (query or "").strip()
    if not q:
        return "HATA: boş sorgu."
    n = max(1, min(int(max_results or 8), 20))
    r, err = _get("https://export.arxiv.org/api/query",
                  {"search_query": f"all:{q}", "max_results": n, "sortBy": "relevance"})
    if err:
        return err
    if r.status_code != 200:
        return f"HATA: arXiv {r.status_code} döndü."
    try:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entries = ET.fromstring(r.text).findall("a:entry", ns)
    except Exception:
        return "HATA: arXiv yanıtı çözümlenemedi."
    if not entries:
        return "SONUÇ YOK"

    lines = []
    for e in entries:
        raw_id = (e.findtext("a:id", default="", namespaces=ns) or "")
        aid = raw_id.rsplit("/abs/", 1)[-1]
        title = " ".join((e.findtext("a:title", default="", namespaces=ns) or "").split())
        authors = ", ".join(
            (a.findtext("a:name", default="", namespaces=ns) or "").strip()
            for a in e.findall("a:author", ns)[:4]) or "(yazar yok)"
        published = (e.findtext("a:published", default="", namespaces=ns) or "")[:10]
        lines.append(f"arXiv:{aid} | {title} | {authors} | {published}")
    return "\n".join(lines)


@function_tool
def search_crossref(query: str, rows: int = 8) -> str:
    """Crossref'te (dergi/konferans yayınları) konuya göre GERÇEK makale arar.

    Args:
        query: Serbest metin arama sorgusu (İngilizce anahtar kelimeler en iyi sonucu verir).
        rows: Döndürülecek kayıt sayısı (1-20, varsayılan 8).

    Returns:
        Her satırda 'DOI=... | başlık | yazarlar | yıl | venue | atıf≈N'; sonuç yoksa
        'SONUÇ YOK'; ağ/servis sorununda 'HATA: ...'.
    """
    return search_crossref_raw(query, rows)


@function_tool
def search_arxiv(query: str, max_results: int = 8) -> str:
    """arXiv'de (preprint) konuya göre GERÇEK makale arar.

    Args:
        query: Serbest metin arama sorgusu (İngilizce anahtar kelimeler en iyi sonucu verir).
        max_results: Döndürülecek kayıt sayısı (1-20, varsayılan 8).

    Returns:
        Her satırda 'arXiv:ID | başlık | yazarlar | tarih'; sonuç yoksa 'SONUÇ YOK';
        ağ/servis sorununda 'HATA: ...'.
    """
    return search_arxiv_raw(query, max_results)


@function_tool
def crossref_lookup(doi: str) -> str:
    """Bir DOI'yi Crossref'te sorgular ve kayıtlı meta veriyi döndürür.

    Args:
        doi: Sorgulanacak DOI (ör. '10.1126/scirobotics.aau5872'). 'https://doi.org/'
             öneki varsa temizlenir.

    Returns:
        Bulunursa 'BULUNDU | başlık | yazarlar | yıl | venue', bulunamazsa
        'BULUNAMADI', ağ/servis sorunu varsa 'HATA: ...'.
    """
    return lookup_doi(doi)


@function_tool
def arxiv_lookup(arxiv_id: str) -> str:
    """Bir arXiv ID'sini arXiv API'sinde sorgular.

    Args:
        arxiv_id: arXiv kimliği (ör. '2310.01234' veya 'arXiv:2310.01234').

    Returns:
        Bulunursa 'BULUNDU | başlık | yazarlar | tarih', bulunamazsa 'BULUNAMADI',
        ağ/servis sorunu varsa 'HATA: ...'.
    """
    return lookup_arxiv(arxiv_id)


# =============================================================================
# GITHUB REPO ARAMA — 'repos' metriği için (Literature Search, RL Coding)
# =============================================================================
def search_github_raw(query: str, limit: int = 5) -> str:
    """search_github aracının saf (test edilebilir) gövdesi."""
    q = (query or "").strip()
    if not q:
        return "HATA: boş sorgu."
    n = max(1, min(int(limit or 5), 10))
    r, err = _get("https://api.github.com/search/repositories",
                  {"q": q, "sort": "stars", "order": "desc", "per_page": n})
    if err:
        return err
    if r.status_code == 403:
        return "HATA: GitHub oran sınırı (anahtarsız erişim saatlik sınırlı)."
    if r.status_code != 200:
        return f"HATA: GitHub {r.status_code} döndü."
    try:
        items = r.json().get("items", [])
    except Exception:
        return "HATA: GitHub yanıtı çözümlenemedi."
    if not items:
        return "SONUÇ YOK"
    lines = []
    for it in items:
        desc = (it.get("description") or "")[:70]
        lines.append(f"{it.get('full_name')} | ⭐{it.get('stargazers_count', 0)} | "
                     f"{it.get('language') or '—'} | güncelleme {(it.get('pushed_at') or '')[:10]} "
                     f"| {desc}")
    return "\n".join(lines)


# =============================================================================
# SEMANTIC SCHOLAR — gerçek atıf sayısı (Crossref yeni yayınlarda ~0 döndürür)
# =============================================================================
def citations_raw(identifier: str) -> str:
    """citation_count aracının saf (test edilebilir) gövdesi.
    identifier: DOI, 'arXiv:XXXX.XXXXX' veya düz arXiv ID."""
    s = (identifier or "").strip()
    if not s:
        return "HATA: boş kimlik."
    s = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", s, flags=re.I).strip()
    m = re.match(r"^arxiv:\s*(.+)$", s, flags=re.I)
    key = f"arXiv:{m.group(1).split('v')[0]}" if m else f"DOI:{s}"
    # Anahtarsiz havuz paylasimli ve cok sik 429 doner. UZUN beklemek pipeline'i
    # dakikalarca durdurur; HIZLI basarisiz olup Crossref atif sayisina dusmek daha iyi.
    r, err = _get(f"https://api.semanticscholar.org/graph/v1/paper/{key}",
                  {"fields": "title,year,citationCount,influentialCitationCount,venue"},
                  retries=2, backoff=1.0)
    if err:
        return (err + " Semantic Scholar oran sınırı olabilir; atıf sayısı için "
                "Crossref'in 'atıf≈N' değerine düşebilirsin.")
    if r.status_code == 404:
        return "BULUNAMADI (Semantic Scholar'da kayıt yok)"
    if r.status_code != 200:
        return f"HATA: Semantic Scholar {r.status_code} döndü."
    try:
        d = r.json()
    except Exception:
        return "HATA: Semantic Scholar yanıtı çözümlenemedi."
    return (f"BULUNDU | atıf={d.get('citationCount', '?')} | "
            f"etkili_atıf={d.get('influentialCitationCount', '?')} | "
            f"yıl={d.get('year', '?')} | venue={d.get('venue') or '—'} | "
            f"{(d.get('title') or '')[:70]}")


# =============================================================================
# İSTATİSTİK — Statistical Analysis ve Ablation ajanları için GERÇEK hesap.
# Ajan p-değeri/GA'yı zihinden uydurmasın; sayılar burada deterministik hesaplanır.
# =============================================================================
def _parse_nums(raw):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", raw or "")]


def summarize_raw(values: str) -> str:
    """describe_sample aracının saf gövdesi: n, ortalama, SD, SEM, %95 GA."""
    xs = _parse_nums(values)
    if len(xs) < 2:
        return "HATA: en az 2 sayı gerekli (virgülle ayır)."
    n = len(xs)
    mean = statistics.fmean(xs)
    sd = statistics.stdev(xs)                      # örneklem SD (n-1)
    sem = sd / math.sqrt(n)
    # t-dagiliminin %97.5 kritik degeri (iki yanli %95), df = n-1
    tcrit = _T95.get(n - 1, 1.96)
    half = tcrit * sem
    return (f"n={n} | ortalama={mean:.4g} | SD={sd:.4g} | SEM={sem:.4g} | "
            f"%95 GA=[{mean - half:.4g}, {mean + half:.4g}] (t={tcrit}, df={n - 1}) | "
            f"min={min(xs):.4g} | max={max(xs):.4g}")


# Iki yanli %95 icin t kritik degerleri (df 1-30); df>30 -> 1.96
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
        15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056,
        27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def _t_sf(t, df):
    """Student-t sag kuyruk olasiligi (regularize edilmis incomplete beta ile)."""
    t = abs(t)
    x = df / (df + t * t)
    return 0.5 * _betainc(df / 2.0, 0.5, x)


def _betainc(a, b, x):
    """Regularize edilmis incomplete beta I_x(a,b) — surekli kesir (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= c * d
        if abs(1.0 - c * d) < 1e-10:
            break
    result = front * (f - 1.0)
    return result if x < (a + 1) / (a + b + 2) else 1.0 - _betainc(b, a, 1 - x)


def compare_raw(group_a: str, group_b: str) -> str:
    """welch_t_test aracının saf gövdesi: Welch t-testi + Cohen's d."""
    xa, xb = _parse_nums(group_a), _parse_nums(group_b)
    if len(xa) < 2 or len(xb) < 2:
        return "HATA: her iki grupta en az 2 sayı gerekli."
    na, nb = len(xa), len(xb)
    ma, mb = statistics.fmean(xa), statistics.fmean(xb)
    va, vb = statistics.variance(xa), statistics.variance(xb)
    if va == 0 and vb == 0:
        return "HATA: iki grupta da varyans sıfır; test tanımsız."
    se = math.sqrt(va / na + vb / nb)
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    p = 2.0 * _t_sf(t, df)
    p = min(1.0, max(0.0, p))
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    d = (ma - mb) / sp if sp else float("nan")
    verdict = "anlamlı (p<0.05)" if p < 0.05 else "anlamlı DEĞİL (p>=0.05)"
    return (f"A: n={na} ortalama={ma:.4g} SD={math.sqrt(va):.4g} | "
            f"B: n={nb} ortalama={mb:.4g} SD={math.sqrt(vb):.4g}\n"
            f"fark={ma - mb:.4g} | Welch t={t:.3f} | df={df:.2f} | p={p:.4g} → {verdict} | "
            f"Cohen's d={d:.3f}")


@function_tool
def search_github(query: str, limit: int = 5) -> str:
    """GitHub'da açık kaynak depo arar (yıldıza göre sıralı).

    Args:
        query: Arama sorgusu (ör. 'wheel-legged reinforcement learning locomotion').
        limit: Döndürülecek depo sayısı (1-10, varsayılan 5).

    Returns:
        Her satırda 'ad | ⭐yıldız | dil | güncelleme | açıklama'; sonuç yoksa
        'SONUÇ YOK'; oran sınırı/ağ sorununda 'HATA: ...'.
    """
    return search_github_raw(query, limit)


@function_tool
def citation_count(identifier: str) -> str:
    """Bir makalenin GERÇEK atıf sayısını Semantic Scholar'dan alır.

    Crossref'in atıf alanı yeni yayınlarda sıfıra yakındır; bu araç daha güvenilirdir.

    Args:
        identifier: DOI veya 'arXiv:XXXX.XXXXX'.

    Returns:
        'BULUNDU | atıf=N | etkili_atıf=N | yıl | venue | başlık', kayıt yoksa
        'BULUNAMADI', oran sınırı/ağ sorununda 'HATA: ...'.
    """
    return citations_raw(identifier)


@function_tool
def describe_sample(values: str) -> str:
    """Bir sayı dizisinin betimsel istatistiğini HESAPLAR (zihinden hesaplama yapma).

    Args:
        values: Virgülle ayrılmış sayılar (ör. '0.41, 0.44, 0.39, 0.42, 0.40').

    Returns:
        'n | ortalama | SD | SEM | %95 GA | min | max' — SD örneklem (n-1) SD'sidir,
        güven aralığı t-dağılımıyla hesaplanır.
    """
    return summarize_raw(values)


@function_tool
def welch_t_test(group_a: str, group_b: str) -> str:
    """İki bağımsız grubu Welch t-testi ile KARŞILAŞTIRIR ve etki büyüklüğü verir.

    p-değerini asla tahmin etme; bu aracı çağır.

    Args:
        group_a: Birinci grup, virgülle ayrılmış sayılar (ör. yöntemin seed sonuçları).
        group_b: İkinci grup, virgülle ayrılmış sayılar (ör. baseline seed sonuçları).

    Returns:
        Her grubun n/ortalama/SD'si, fark, Welch t, df, p-değeri, anlamlılık kararı
        ve Cohen's d. Veri yetersizse 'HATA: ...'.
    """
    return compare_raw(group_a, group_b)


# ---------------------------------------------------------------- arac gruplari
SEARCH_TOOLS = [search_crossref, search_arxiv]              # literatür arama
VERIFICATION_TOOLS = [crossref_lookup, arxiv_lookup]        # kimlik doğrulama
STATS_TOOLS = [describe_sample, welch_t_test]               # gerçek hesap
# Literature Search: arama + atıf + repo (5 metriğin 3'ü artık ölçülebilir)
LITERATURE_TOOLS = SEARCH_TOOLS + [citation_count, search_github]
