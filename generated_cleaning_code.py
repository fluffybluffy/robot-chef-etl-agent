names = ['imdb_id', 'title', 'release_date', 'genres', 'duration_min', 'country', 'content_rating', 'director', 'income_usd', 'votes', 'imdb_score']
df = df.replace(r'^\s*$', np.nan, regex=True)
df = df.dropna(axis=0, how='all')
df = df.dropna(axis=1, how='all')
df.columns = names
df = df.reset_index(drop=True)

for c in ['imdb_id', 'title', 'genres', 'director']:
    df[c] = df[c].map(lambda v: v.strip() if isinstance(v, str) else v)

months = {'jan':1,'ene':1,'feb':2,'mar':3,'apr':4,'abr':4,'may':5,'jun':6,'jul':7,'aug':8,'ago':8,'sep':9,'set':9,'oct':10,'nov':11,'dec':12,'dic':12}
stop = {'the', 'of', 'year', 'del', 'de'}

def parse_date(x):
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    if not s:
        return None
    s = re.sub(r'(\d)(st|nd|rd|th)\b', r'\1', s)
    words = [w for w in re.findall(r'[^\W\d_]+', s) if w not in stop and len(w) >= 3 and w[:3] in months]
    nums = re.findall(r'\d+', s)
    try:
        if words:
            m = months[words[0][:3]]
            if len(nums) != 2:
                return None
            if len(nums[0]) == 4:
                y, d = nums[0], nums[1]
            else:
                d, y = nums[0], nums[1]
        else:
            if len(nums) != 3:
                return None
            a, b, c = nums
            if len(a) == 4:
                y, m, d = a, b, c
            else:
                y = c
                ai, bi = int(a), int(b)
                if ai > 12:
                    d, m = a, b
                elif bi > 12:
                    m, d = a, b
                elif len(c) == 4 and re.search(r'[/-]', s):
                    d, m = a, b
                else:
                    m, d = a, b
        if len(str(y)) <= 2:
            yy = int(y)
            yr = 1900 + yy if yy > 26 else 2000 + yy
        else:
            yr = int(y)
        ts = pd.Timestamp(year=yr, month=int(m), day=int(d))
        return ts.strftime('%Y-%m-%d')
    except Exception:
        return None

df['release_date'] = df['release_date'].map(parse_date)

def dur(x):
    if pd.isna(x):
        return np.nan
    m = re.match(r'^\s*(\d+)(?:\.0+)?\s*[A-Za-z]*\s*$', str(x))
    return float(m.group(1)) if m else np.nan

df['duration_min'] = pd.to_numeric(df['duration_min'].map(dur), errors='coerce').round().astype('Int64')

cmap = {'US': 'USA', 'USA': 'USA', 'U.S.': 'USA', 'U.S.A': 'USA', 'New Zesland': 'New Zealand', 'New Zeland': 'New Zealand'}
def ctry(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    s = re.sub(r'[\d.]+$', '', s).strip()
    return cmap.get(s, s)

df['country'] = df['country'].map(ctry)

rmap = {'G': 'G', 'PG': 'PG', 'PG-13': 'PG-13', 'R': 'R', 'UNRATED': 'Not Rated', 'NOT RATED': 'Not Rated', 'APPROVED': 'Not Rated'}
def rating(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    return rmap.get(s.upper(), s)

df['content_rating'] = df['content_rating'].map(rating)

def inc(x):
    if pd.isna(x):
        return np.nan
    s = re.sub(r'[\s$,]', '', str(x))
    s = s.replace('o', '0').replace('O', '0')
    if re.fullmatch(r'\d+(\.\d+)?', s):
        return float(s)
    return np.nan

inc_num = pd.to_numeric(df['income_usd'].map(inc), errors='coerce')
inc_num = inc_num.where(inc_num >= 100000)
df['income_usd'] = inc_num.round().astype('Int64')

def vot(x):
    if pd.isna(x):
        return np.nan
    s = re.sub(r'[\s.,]', '', str(x))
    if re.fullmatch(r'\d+', s):
        return float(s)
    return np.nan

df['votes'] = pd.to_numeric(df['votes'].map(vot), errors='coerce').round().astype('Int64')

def score(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip().lower()
    s = re.sub(r'e[-+]?0*$', '', s)
    s = re.sub(r'[,:;]', '.', s)
    s = re.sub(r'[^0-9.]', '', s)
    s = re.sub(r'\.+', '.', s).strip('.')
    if re.fullmatch(r'\d+(\.\d+)?', s):
        v = float(s)
        if 0 <= v <= 10:
            return v
    return np.nan

df['imdb_score'] = pd.to_numeric(df['income_usd'].map(lambda v: np.nan) if False else df['imdb_score'].map(score), errors='coerce').astype(float)

df = df[names].reset_index(drop=True)