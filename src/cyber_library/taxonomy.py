from __future__ import annotations

import re
from collections import Counter

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "Literature": ("fiction", "literature", "novel", "novels", "poetry", "poems", "drama", "short stories", "literary", "小说", "文学", "诗歌", "戏剧", "故事", "小説", "文学作品"),
    "Children & Young Adult": ("juvenile", "children", "young adult", "picture books", "童书", "儿童", "青少年", "绘本", "児童書", "絵本"),
    "Philosophy": ("philosophy", "ethics", "logic", "epistemology", "metaphysics", "哲学", "伦理", "逻辑", "认识论", "形而上学", "倫理学", "論理学"),
    "History": ("history", "historical", "biography", "archaeology", "civilization", "历史", "传记", "考古", "文明", "歴史", "伝記"),
    "Religion": ("religion", "theology", "bible", "buddhism", "christianity", "islam", "宗教", "神学", "佛教", "基督教", "伊斯兰", "神学", "仏教"),
    "Social Sciences": ("sociology", "anthropology", "politics", "political science", "psychology", "social science", "society", "社会学", "人类学", "政治学", "心理学", "社会科学", "人類学"),
    "Business & Economics": ("business", "management", "marketing", "finance", "economics", "entrepreneurship", "accounting", "商业", "管理", "市场营销", "金融", "经济", "会计", "経済", "会計"),
    "Law": ("law", "legal", "jurisprudence", "法律", "法学", "法学"),
    "Education": ("education", "teaching", "pedagogy", "schools", "教育", "教学", "教育学", "教育学"),
    "Mathematics": ("mathematics", "algebra", "geometry", "calculus", "statistics", "数学", "代数", "几何", "微积分", "统计", "幾何", "統計学"),
    "Physics": ("physics", "mechanics", "quantum", "relativity", "optics", "物理", "力学", "量子", "相对论", "光学", "物理学", "相対性理論"),
    "Chemistry": ("chemistry", "chemical", "化学"),
    "Biology": ("biology", "ecology", "evolution", "genetics", "zoology", "botany", "生物", "生态", "进化", "遗传", "动物学", "植物学", "生物学", "進化"),
    "Medicine & Health": ("medicine", "medical", "health", "anatomy", "physiology", "nursing", "医学", "医疗", "健康", "解剖", "生理", "护理", "看護"),
    "Engineering": ("engineering", "electronics", "electrical", "mechanical", "civil engineering", "robotics", "工程", "电子", "电气", "机械", "土木", "机器人", "工学", "ロボット工学"),
    "Computer Science": ("computer", "computing", "programming", "software", "algorithm", "algorithms", "artificial intelligence", "machine learning", "data science", "database", "cybersecurity", "information technology", "计算机", "编程", "软件", "算法", "人工智能", "机器学习", "数据科学", "数据库", "网络安全", "コンピュータ", "プログラミング", "人工知能", "機械学習", "データサイエンス"),
    "Arts & Design": ("art", "arts", "design", "music", "photography", "architecture", "painting", "艺术", "设计", "音乐", "摄影", "建筑", "绘画", "芸術", "音楽", "写真"),
    "Language & Linguistics": ("language", "linguistics", "grammar", "translation", "dictionary", "语言", "语言学", "语法", "翻译", "词典", "辞典", "言語学", "翻訳"),
    "Geography & Travel": ("geography", "travel", "maps", "atlas", "地理", "旅行", "旅游", "地图", "地理学", "地図"),
    "Reference": ("encyclopedia", "encyclopedias", "handbook", "reference", "dictionaries", "百科", "手册", "参考书", "百科事典"),
}

CATEGORY_LABELS_ZH = {"Literature":"文学","Children & Young Adult":"儿童与青少年","Philosophy":"哲学","History":"历史","Religion":"宗教","Social Sciences":"社会科学","Business & Economics":"商业与经济","Law":"法律","Education":"教育","Mathematics":"数学","Physics":"物理","Chemistry":"化学","Biology":"生物","Medicine & Health":"医学与健康","Engineering":"工程","Computer Science":"计算机科学","Arts & Design":"艺术与设计","Language & Linguistics":"语言与语言学","Geography & Travel":"地理与旅行","Reference":"工具书","Unclassified":"未分类"}

SUBJECT_ALIASES = {
    "人工智能": "Artificial intelligence", "人工知能": "Artificial intelligence", "ai": "Artificial intelligence",
    "机器学习": "Machine learning", "機械学習": "Machine learning",
    "计算机科学": "Computer science", "計算機科学": "Computer science", "コンピュータ科学": "Computer science",
    "数据科学": "Data science", "データサイエンス": "Data science",
    "数据库": "Databases", "データベース": "Databases",
    "网络安全": "Cybersecurity", "サイバーセキュリティ": "Cybersecurity",
    "数学": "Mathematics", "統計学": "Statistics", "统计学": "Statistics", "统计": "Statistics",
    "物理学": "Physics", "物理": "Physics", "量子力学": "Quantum mechanics", "量子力学": "Quantum mechanics",
    "化学": "Chemistry", "生物学": "Biology", "生物": "Biology",
    "哲学": "Philosophy", "伦理学": "Ethics", "倫理学": "Ethics", "逻辑学": "Logic", "論理学": "Logic",
    "历史": "History", "歴史": "History", "文学": "Literature", "小説": "Fiction", "小说": "Fiction",
    "经济学": "Economics", "経済学": "Economics", "心理学": "Psychology", "社会学": "Sociology",
    "医学": "Medicine", "教育学": "Education", "教育": "Education", "法律": "Law", "法学": "Law",
    "机器人": "Robotics", "ロボット工学": "Robotics", "语言学": "Linguistics", "言語学": "Linguistics",
}


def categories() -> list[str]: return list(CATEGORY_RULES)+["Unclassified"]


def normalize_subject(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()
    if not text: return ""
    return SUBJECT_ALIASES.get(text.casefold(), SUBJECT_ALIASES.get(text, text))


def normalize_subjects(values: list[str] | None, limit: int = 64) -> list[str]:
    out=[]; seen=set()
    for value in values or []:
        text=normalize_subject(str(value)); key=text.casefold()
        if not text or key in seen: continue
        seen.add(key); out.append(text)
        if len(out)>=limit: break
    return out


def classify(subjects: list[str] | None, title: str = "", description: str = "", limit: int = 3) -> list[str]:
    normalized=normalize_subjects(subjects,128)
    haystack=" ".join([title,description,*normalized,*(subjects or [])]).casefold(); scores:Counter[str]=Counter()
    for category,patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            p=pattern.casefold()
            if not p: continue
            if re.search(r"[\u3040-\u30ff\u3400-\u9fff]",p): count=haystack.count(p)
            else:
                count=len(re.findall(rf"(?<!\w){re.escape(p)}(?!\w)",haystack))
                if count==0 and " " in p: count=haystack.count(p)
            if count:scores[category]+=count
    if not scores:return ["Unclassified"]
    return [name for name,_ in scores.most_common(max(1,limit))]


def normalize_tags(values: list[str] | None, limit: int = 32) -> list[str]:
    out=[]; seen=set()
    for value in values or []:
        text=re.sub(r"\s+"," ",str(value)).strip(); key=text.casefold()
        if not text or key in seen: continue
        seen.add(key); out.append(text)
        if len(out)>=limit:break
    return out
