"""Gộp alias bổ sung vào skill_taxonomy.json (chạy lặp lại không bị trùng).

Chỉ thêm alias cho skill CÓ SẴN, không thêm skill mới (seed_dev.py kiểm tra đúng 135 skill).
Chạy:  python -m scripts.add_aliases   rồi   python -m scripts.seed_dev
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "ai-service" / "app" / "core" / "skill_taxonomy.json"

EXTRA = {
    "JavaScript": ["ES6", "ECMAScript"],
    "TypeScript": ["TS"],
    "Python": ["Python3", "Python 3"],
    "C#": ["CSharp", "C Sharp"],
    "C++": ["CPP"],
    "Go": ["Golang"],
    "Node.js": ["NodeJS", "Node JS"],
    "Express.js": ["ExpressJS", "Express"],
    "NestJS": ["Nest.js"],
    "Next.js": ["Next JS"],
    "Spring Boot": ["SpringBoot", "Spring"],
    ".NET Core": [".NET", "dotnet"],
    "ASP.NET": ["ASP.NET MVC", "ASP.NET Core"],
    "PostgreSQL": ["Postgres", "Postgre SQL"],
    "MongoDB": ["Mongo"],
    "SQL Server": ["MSSQL", "MS SQL", "Microsoft SQL Server"],
    "AWS": ["Amazon Web Services"],
    "Google Cloud": ["GCP", "Google Cloud Platform"],
    "Kubernetes": ["K8s"],
    "GitLab CI/CD": ["GitLab CI", "CI/CD"],
    "Machine Learning": ["ML", "Học máy", "Máy học"],
    "Deep Learning": ["DL", "Học sâu"],
    "NLP": ["Natural Language Processing", "Xử lý ngôn ngữ tự nhiên"],
    "Computer Vision": ["Thị giác máy tính"],
    "Scikit-learn": ["sklearn", "scikit learn"],
    "Hugging Face": ["HuggingFace"],
    "LLM": ["Large Language Model", "Large Language Models"],
    "Power BI": ["PowerBI"],
    "Excel": ["Microsoft Excel", "MS Excel"],
    "Manual Testing": ["Kiểm thử thủ công", "Manual Test"],
    "Automation Testing": ["Kiểm thử tự động", "Automation Test", "Automated Testing"],
    "Test Case": ["Testcase", "Test Cases"],
    "REST API": ["RESTful API", "RESTful", "REST APIs", "RESTful APIs"],
    "SASS/SCSS": ["SASS", "SCSS"],
    "Tailwind CSS": ["TailwindCSS"],
    "React Native": ["ReactNative"],
    "Microservices": ["Microservice"],
    "ELK Stack": ["ELK", "Elastic Stack"],
    "Spark": ["Apache Spark", "PySpark"],
    "Kafka": ["Apache Kafka"],
    "Airflow": ["Apache Airflow"],
    "Cybersecurity": ["Cyber Security", "An ninh mạng", "An toàn thông tin"],
    "Penetration Testing": ["Pentest", "Pen Test"],
    "Facebook Ads": ["Meta Ads"],
    "Google Analytics": ["GA4"],
    "Data Warehouse": ["DWH", "Kho dữ liệu"],
    "Illustrator": ["Adobe Illustrator"],
    "Photoshop": ["Adobe Photoshop"],
}


def main() -> None:
    items = json.loads(PATH.read_text(encoding="utf-8"))
    by_name = {i["skill"]: i for i in items}
    unknown = [k for k in EXTRA if k not in by_name]
    if unknown:
        raise SystemExit(f"Không có skill này trong taxonomy: {unknown}")
    added = 0
    for name, aliases in EXTRA.items():
        item = by_name[name]
        have = {a.casefold() for a in item["aliases"]} | {name.casefold()}
        for alias in aliases:
            if alias.casefold() not in have:
                item["aliases"].append(alias)
                have.add(alias.casefold())
                added += 1
    PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã thêm {added} alias, tổng {len(items)} skill.")


if __name__ == "__main__":
    main()
