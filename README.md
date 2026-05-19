# CSV 自动入库 MySQL Skill

## 功能

这个 Skill 用于把 CSV 文件自动导入 MySQL。

主要能力：

- 读取 CSV 第一行作为表头；
- 自动处理空字段名、重复字段名、超长字段名；
- 自动统计每一列最大字符长度；
- 自动创建 MySQL 表；
- 所有字段统一使用 `VARCHAR`；
- 支持按最大长度加冗余；
- 支持只生成建表 SQL；
- 支持批量导入数据；
- 支持空字符串转 NULL；
- 支持旧表删除重建。

## 目录结构

```text
csv-to-mysql-varchar/
├── SKILL.md
├── requirements.txt
├── README.md
├── scripts/
│   └── csv_to_mysql_varchar.py
└── examples/
    └── run_example.bat
```

## 安装依赖

进入 Skill 目录：

```bat
cd /d D:\cherry-skills\csv-to-mysql-varchar
```

安装依赖：

```bat
pip install -r requirements.txt
```

## 基础用法

```bat
python scripts\csv_to_mysql_varchar.py ^
  --csv "D:\data\patient.csv" ^
  --host 127.0.0.1 ^
  --port 3306 ^
  --user root ^
  --password 123456 ^
  --database test ^
  --table patient_import ^
  --encoding utf-8-sig ^
  --drop
```

## 只生成 SQL，不导入

```bat
python scripts\csv_to_mysql_varchar.py ^
  --csv "D:\data\patient.csv" ^
  --database test ^
  --table patient_import ^
  --only-sql
```

## 常用参数说明

| 参数 | 说明 |
|---|---|
| `--csv` | CSV 文件路径 |
| `--host` | MySQL 地址 |
| `--port` | MySQL 端口 |
| `--user` | MySQL 用户名 |
| `--password` | MySQL 密码 |
| `--database` | 数据库名 |
| `--table` | 目标表名 |
| `--encoding` | CSV 编码，常用 `utf-8-sig` 或 `gbk` |
| `--drop` | 如果表存在，先删除再创建 |
| `--only-sql` | 只生成建表 SQL，不连接数据库 |
| `--strict-max` | 严格按照 CSV 最大长度创建 VARCHAR |
| `--min-length` | VARCHAR 最小长度，默认 20 |
| `--length-factor` | 长度冗余倍数，默认 1.2 |
| `--max-varchar-length` | VARCHAR 最大长度，默认 1000 |
| `--batch-size` | 批量插入大小，默认 1000 |

## 字段长度规则

默认规则：

```text
建表长度 = max(ceil(列最大字符长度 * 1.2), 20)
```

然后再限制最大长度：

```text
建表长度 <= max_varchar_length
```

默认：

```text
max_varchar_length = 1000
```

例如：

| 原始最大长度 | 默认建表长度 |
|---:|---:|
| 3 | VARCHAR(20) |
| 18 | VARCHAR(22) |
| 100 | VARCHAR(120) |
| 900 | VARCHAR(1000) |

## 注意事项

1. 所有字段都是 VARCHAR，不做类型推断。
2. `--drop` 会删除旧表，正式库慎用。
3. 如果 CSV 列非常多，并且每列 VARCHAR 都很长，MySQL 可能因为单行最大长度限制导致建表失败。
4. 如果遇到中文乱码，优先尝试：
   - `--encoding utf-8-sig`
   - `--encoding gbk`
5. 如果 CSV 不是逗号分隔，可以使用 `--delimiter` 指定分隔符。
