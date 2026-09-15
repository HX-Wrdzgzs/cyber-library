from __future__ import annotations

import re
from collections import Counter

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "Literature": ("fiction", "literature", "novel", "novels", "poetry", "poems", "drama", "short stories", "literary", "小说", "文学", "诗歌", "戏剧", "故事"),
    "Children & Young Adult": ("juvenile", "children", "young adult", "picture books", "童书", "儿童", "青少年", "绘本"),
    "Philosophy": ("philosophy", "ethics", "logic", "epistemology", "metaphysics", "哲学", "伦理", "逻辑", "认识论", "形而上学"),
    "History": ("history", "historical", "biography", "archaeology", "civilization", "历史", "传记", "考古", "文明"),
    "Religion": ("religion", "theology", "bible", "buddhism", "christianity", "islam", "宗教", "神学", "佛教", "基督教", "伊斯兰"),
    "Social Sciences": ("sociology", "anthropology", "politics", "political science", "psychology", "social science", "society", "社会学", "人类学", "政治学", "心理学", "社会科学"),
    "Business & Economics": ("business", "management", "marketing", "finance", "economics", "entrepreneurship", "accounting", "商业", "管理", "市场营销", "金融", "经济", "会计"),
    "Law": ("law", "legal", "jurisprudence", "法律", "法学"),
    "Education": ("education", "teaching", "pedagogy", "schools", "教育", "教学", "教育学"),
    "Mathematics": ("mathematics", "algebra", "geometry", "calculus", "statistics", "数学", "代数", "几何", "微积分", "统计"),
    "Physics": ("physics", "mechanics", "quantum", "relativity", "optics", "物理", "力学", "量子", "相对论", "光学"),
    "Chemistry": ("chemistry", "chemical", "化学"),
    "Biology": ("biology", "ecology", "evolution", "genetics", "zoology", "botany", "生物", "生态", "进化", "遗传", "动物学", "植物学"),
    "Medicine & Health": ("medicine", "medical", "health", "anatomy", "physiology", "nursing", "医学", "医疗", "健康", "解剖", "生理", "护理"),
    "Engineering": ("engineering", "electronics", "electrical", "mechanical", "civil engineering", "robotics", "工程", "电子", "电气", "机械", "土木", "机器人"),
    "Computer Science": ("computer", "computing", "programming", "software", "algorithm", "algorithms", "artificial intelligence", "machine learning", "data science", "database", "cybersecurity", "information technology", "计算机", "编程", "软件", "算法", "人工智能", "机器学习", "数据科学", "数据库", "网络安全"),
    "Arts & Design": ("art", "arts", "design", "music", "photography", "architecture", "painting", "艺术", "设计", "音乐", "摄影", "建筑", "绘画"),
    "Language & Linguistics": ("language", "linguistics", "grammar", "translation", "dictionary", "语言", "语言学", "语法", "翻译", "词典", "辞典"),
    "Geography & Travel": ("geography", "travel", "maps", "atlas", "地理", "旅行", "旅游", "地图"),
    "Reference": ("encyclopedia", "encyclopedias", "handbook", "reference", "dictionaries", "百科", "手册", "参考书"),
}

CATEGORY_LABELS_ZH = {"Literature":"文学","Children & Young Adult":"儿童与青少年","Philosophy":"哲学","History":"历史","Religion":"宗教","Social Sciences":"社会科学","Business & Economics":"商业与经济","Law":"法律","Education":"教育","Mathematics":"数学","Physics":"物理","Chemistry":"化学","Biology":"生物","Medicine & Health":"医学与健康","Engineering":"工程","Computer Science":"计算机科学","Arts & Design":"艺术与设计","Language & Linguistics":"语言与语言学","Geography & Travel":"地理与旅行","Reference":"工具书","Unclassified":"未分类"}

def categories() -> list[str]: return list(CATEGORY_RULES)+["Unclassified"]

def classify(subjects: list[str] | None, title: str = "", description: str = "", limit: int = 3) -> list[str]:
    haystack=" ".join([title,description,*(subjects or [])]).casefold(); scores:Counter[str]=Counter()
    for category,patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            p=pattern.casefold()
            if not p: continue
            if re.search(r"[\u3400-\u9fff]",p): count=haystack.count(p)
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
