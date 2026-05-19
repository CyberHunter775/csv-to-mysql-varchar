---
name: csv-to-mysql-varchar
description: 将 CSV 文件自动写入 MySQL，自动创建表，所有 CSV 字段统一使用 VARCHAR，并根据每列最大字符长度设置字段长度。
---

# CSV 自动入库 MySQL 技能

## 技能用途

当用户需要把 CSV 文件导入 MySQL，并希望自动创建表时，使用本技能。

适用场景：

- CSV 第一行为表头；
- 根据 CSV 表头自动创建 MySQL 字段；
- 所有字段统一使用 VARCHAR；
- 根据每一列实际最大字符长度设置 VARCHAR 长度；
- 自动批量插入 CSV 数据；
- 适合临时数据入库、数据清洗前落库、Excel/CSV 原始数据留存。

## 固定规则

1. 所有 CSV 字段都使用 VARCHAR 类型。
2. 不自动推断 INT、DECIMAL、DATE、DATETIME、TEXT、JSON 等类型。
3. CSV 第一行作为字段名。
4. 字段名需要安全处理：
   - 去掉前后空格；
   - 空字段名改为 col_序号；
   - 重复字段名追加 _2、_3；
   - 字段名过长时自动截断，避免超过 MySQL 字段名长度限制；
   - MySQL 字段名使用反引号包裹。
5. 自动增加主键字段：

```sql
`id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID'
```

6. 字段长度计算规则：

```text
字段实际最大长度 = CSV 中该列所有值的最大字符长度
默认建表长度 = max(ceil(字段实际最大长度 * 1.2), 20)
```

7. 如果用户要求严格按照最大长度，则使用：

```text
建表长度 = max(字段实际最大长度, 1)
```

8. 默认 VARCHAR 最大长度为 1000。
9. 如果用户明确要求，可以改为 2000、4000 或其他值。
10. 导入时，空字符串默认转为 NULL。
11. 默认批量插入大小为 1000 行。
12. 默认建表字符集为 utf8mb4。
13. 如果用户要求覆盖旧表，则使用 DROP TABLE IF EXISTS。
14. 涉及正式库、生产库、已有表时，需要提醒用户谨慎使用 --drop。

## 使用脚本

本技能使用以下脚本：

```text
scripts/csv_to_mysql_varchar.py
```

## 依赖安装

运行前需要安装：

```bash
pip install -r requirements.txt
```

## 常用命令格式

Windows CMD 示例：

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

如果 CSV 是 GBK 编码：

```bat
python scripts\csv_to_mysql_varchar.py ^
  --csv "D:\data\patient.csv" ^
  --host 127.0.0.1 ^
  --port 3306 ^
  --user root ^
  --password 123456 ^
  --database test ^
  --table patient_import ^
  --encoding gbk ^
  --drop
```

只生成建表 SQL，不真正连接数据库、不导入数据：

```bat
python scripts\csv_to_mysql_varchar.py ^
  --csv "D:\data\patient.csv" ^
  --database test ^
  --table patient_import ^
  --only-sql
```

严格按照 CSV 当前最大长度建表，不加 1.2 倍冗余：

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
  --drop ^
  --strict-max
```

## 交互要求

当用户提出 CSV 入库需求时，需要询问或提取以下参数：

- CSV 文件路径；
- MySQL host；
- MySQL port；
- MySQL user；
- MySQL password；
- database；
- table；
- CSV 编码，默认 utf-8-sig；
- 是否删除旧表重建；
- 是否严格按最大长度建表。

如果用户已经提供了这些信息，不要重复询问，直接生成命令。

## 输出要求

每次回答用户时，优先输出：

1. 处理逻辑；
2. 可执行命令；
3. 需要注意的问题；
4. 如有必要，给出脚本修改建议。

不要编造已经导入成功，除非用户提供了执行日志。
