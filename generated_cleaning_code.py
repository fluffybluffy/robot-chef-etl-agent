df = df.copy()
tmp = df.replace(r'^\s*$', np.nan, regex=True)
keep_rows = tmp.notna().any(axis=1)
keep_cols = tmp.notna().any(axis=0)
df = df.loc[keep_rows, keep_cols].reset_index(drop=True)
df.columns = ['imdb_id', 'title', 'release_date', 'genres', 'duration_min', 'country', 'content_rating', 'director', 'income_usd', 'votes', 'imdb_score']

def clean_str(v):
    if v is None or pd.isna(v):
        return None
    s = str(v).strip()
    return s if s else None

for c in ['imdb_id', 'title', 'genres', 'director']:
    df[c] = df[c].apply(clean_str).astype(object)

MONTHS = {'jan':1,'ene':1,'gen':1,'feb':2,'fev':2,'mar':3,'mär':3,'apr':4,'abr':4,'avr':4,'may':5,'mai':5,'mag':5,'jun':6,'jul':7,'aug':8,'ago':8,'aou':8,'sep':9,'set':9,'oct':10,'okt':10,'ott':10,'nov':11,'dec':12,'dez':12,'dic':12}

def mk(y, m, d):
    try:
        return pd.Timestamp(year=int(y), month=int(m), day=int(d)).strftime('%Y-%m-%d')
    except Exception:
        return None

def fy(ys):
    n = int(ys)
    if len(ys) <= 2:
        n = 1900 + n if n > 26 else 2000 + n
    return n

def parse_date(v):
    if v is None or pd.isna(v):
        return None
    s = str(v).strip()
    if not s:
        return None
    nums = re.findall(r'\d+', s)
    words = re.findall(r'[^\W\d_]+', s)
    month = None
    for w in words:
        if len(w) >= 3 and w[:3].lower() in MONTHS:
            month = MONTHS[w[:3].lower()]
            break
    if month:
        if len(nums) != 2:
            return None
        a, b = nums
        if len(a) == 4:
            y, d = a, b
        else:
            d, y = a, b
        return mk(fy(y), month, d)
    if len(nums) != 3:
        return None
    a, b, c = nums
    if len(a) == 4:
        return mk(int(a), int(b), int(c))
    y = fy(c)
    x = int(a)
    z = int(b)
    if x > 12:
        d, m = x, z
    elif z > 12:
        m, d = x, z
    elif '/' in s:
        d, m = x, z
    else:
        m, d = x, z
    return mk(y, m, d)

df['release_date'] = df['release_date'].apply(parse_date).astype(object)

dur = df['duration_min'].apply(lambda v: None if v is None or pd.isna(v) else str(v)).str.extract(r'(\d+(?:\.\d+)?)')[0]
df['duration_min'] = pd.to_numeric(dur, errors='coerce').round().astype('Int64')

def clean_country(v):
    s = clean_str(v)
    if s is None:
        return None
    s = re.sub(r'\d+$', '', s).strip().rstrip('.').strip()
    if s.upper() in ('US', 'USA', 'U.S', 'U.S.A'):
        return 'USA'
    if re.match(r'^New Ze\w*land$', s, flags=re.I):
        return 'New Zealand'
    return s if s else None

df['country'] = df['country'].apply(clean_country).astype(object)

CR = {'g': 'G', 'pg': 'PG', 'pg-13': 'PG-13', 'r': 'R', 'unrated': 'Not Rated', 'not rated': 'Not Rated', 'approved': 'Approved'}

def clean_cr(v):
    s = clean_str(v)
    if s is None:
        return None
    return CR.get(s.lower(), s)

df['content_rating'] = df['content_rating'].apply(clean_cr).astype(object)

def clean_income(v):
    s = clean_str(v)
    if s is None:
        return None
    s = s.replace('$', '')
    s = re.sub(r'[\s,]', '', s)
    s = s.replace('o', '0').replace('O', '0')
    return s

inc = df['income_usd'].apply(clean_income)
df['income_usd'] = pd.to_numeric(inc, errors='coerce').round().astype('Int64')

def clean_votes(v):
    s = clean_str(v)
    if s is None:
        return None
    return re.sub(r'[.,\s]', '', s)

vt = df['votes'].apply(clean_votes)
df['votes'] = pd.to_numeric(vt, errors='coerce').round().astype('Int64')

def clean_score(v):
    s = clean_str(v)
    if s is None:
        return None
    s = re.sub(r'[eE][-+]?\d*$', '', s)
    s = re.sub(r'[,:;]', '.', s)
    s = re.sub(r'[^0-9.]', '', s)
    s = re.sub(r'\.+', '.', s).strip('.')
    if not s or s.count('.') > 1:
        return None
    return s

sc = pd.to_numeric(df['imdb_score'].apply(clean_score), errors='coerce').astype(float)
sc = sc.where((sc >= 0) & (sc <= 10))
df['imdb_score'] = sc

df = df[['imdb_id', 'title', 'release_date', 'genres', 'duration_min', 'country', 'content_rating', 'director', 'income_usd', 'votes', 'imdb_score']].reset_index(drop=True)