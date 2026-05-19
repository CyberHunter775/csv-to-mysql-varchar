import argparse
import csv
import math
import sys
from pathlib import Path

import mysql.connector


MYSQL_IDENTIFIER_MAX_LEN = 64


def quote_identifier(name: str) -> str:
    """
    MySQL 表名 / 字段名加反引号。
    """
    return "`" + name.replace("`", "``") + "`"


def clean_identifier_name(name: str, default_name: str) -> str:
    """
    清理字段名：
    - 去掉前后空格；
    - 空字段名使用默认名；
    - 超过 MySQL 标识符长度限制时截断。
    """
    name = "" if name is None else str(name).strip()
    if not name:
        name = default_name

    # MySQL 标识符长度上限通常是 64 个字符。
    # 为了给重复后缀预留空间，这里截断到 55。
    if len(name) > 55:
        name = name[:55]

    return name


def normalize_headers(headers):
    """
    处理 CSV 表头：
    1. 去掉前后空格；
    2. 空表头自动命名 col_1、col_2；
    3. 重复表头自动加后缀；
    4. 超长表头截断。
    """
    result = []
    counter = {}

    for idx, h in enumerate(headers, start=1):
        base_name = clean_identifier_name(h, f"col_{idx}")

        if base_name not in counter:
            counter[base_name] = 1
            result.append(base_name)
        else:
            counter[base_name] += 1
            suffix = f"_{counter[base_name]}"
            max_base_len = MYSQL_IDENTIFIER_MAX_LEN - len(suffix)
            result.append(base_name[:max_base_len] + suffix)

    return result


def fix_row_length(row, column_count):
    """
    保证每行列数和表头一致：
    - 少了补空；
    - 多了截断。
    """
    if len(row) < column_count:
        return row + [""] * (column_count - len(row))
    if len(row) > column_count:
        return row[:column_count]
    return row


def analyze_csv(csv_file, encoding, delimiter):
    """
    扫描 CSV，统计每一列最大字符长度。
    """
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 文件不存在：{csv_file}")

    with open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)

        try:
            raw_headers = next(reader)
        except StopIteration:
            raise ValueError("CSV 文件为空，无法读取表头")

        headers = normalize_headers(raw_headers)
        column_count = len(headers)
        max_lengths = [0] * column_count
        row_count = 0

        for row in reader:
            row = fix_row_length(row, column_count)
            row_count += 1

            for i, value in enumerate(row):
                value = "" if value is None else str(value)
                max_lengths[i] = max(max_lengths[i], len(value))

    return headers, max_lengths, row_count


def calc_varchar_length(
    max_len,
    min_length=20,
    length_factor=1.2,
    max_varchar_length=1000,
    strict_max=False,
):
    """
    计算 VARCHAR 长度。
    """
    if strict_max:
        length = max(max_len, 1)
    else:
        length = math.ceil(max_len * length_factor)
        length = max(length, min_length)

    length = min(length, max_varchar_length)
    return length


def build_create_table_sql(
    table_name,
    headers,
    max_lengths,
    min_length,
    length_factor,
    max_varchar_length,
    strict_max,
):
    """
    生成 CREATE TABLE SQL。
    """
    columns = []
    columns.append("`id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID'")

    for col_name, max_len in zip(headers, max_lengths):
        varchar_len = calc_varchar_length(
            max_len=max_len,
            min_length=min_length,
            length_factor=length_factor,
            max_varchar_length=max_varchar_length,
            strict_max=strict_max,
        )

        columns.append(
            f"{quote_identifier(col_name)} VARCHAR({varchar_len}) NULL COMMENT 'CSV字段，原始最大长度：{max_len}'"
        )

    columns.append("PRIMARY KEY (`id`)")

    sql = f"""
CREATE TABLE {quote_identifier(table_name)} (
    {",\n    ".join(columns)}
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='CSV自动导入表';
""".strip()

    return sql


def create_table(conn, table_name, create_sql, drop_first):
    """
    创建 MySQL 表。
    """
    cursor = conn.cursor()

    if drop_first:
        cursor.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")

    cursor.execute(create_sql)
    conn.commit()
    cursor.close()


def insert_csv(
    conn,
    csv_file,
    encoding,
    delimiter,
    table_name,
    headers,
    batch_size,
    empty_as_null=True,
):
    """
    批量插入 CSV 数据。
    """
    cursor = conn.cursor()

    column_sql = ", ".join(quote_identifier(h) for h in headers)
    placeholders = ", ".join(["%s"] * len(headers))

    insert_sql = f"""
INSERT INTO {quote_identifier(table_name)}
({column_sql})
VALUES ({placeholders})
""".strip()

    total = 0
    batch = []
    column_count = len(headers)

    with open(csv_file, "r", encoding=encoding, newline="") as f:
        reader = csv.reader(f, delimiter=delimiter)

        # 跳过表头
        next(reader)

        for row in reader:
            row = fix_row_length(row, column_count)

            if empty_as_null:
                row = [None if v == "" else v for v in row]

            batch.append(row)

            if len(batch) >= batch_size:
                cursor.executemany(insert_sql, batch)
                conn.commit()
                total += len(batch)
                print(f"已导入 {total} 行")
                batch.clear()

        if batch:
            cursor.executemany(insert_sql, batch)
            conn.commit()
            total += len(batch)
            print(f"已导入 {total} 行")

    cursor.close()
    return total


def print_column_analysis(headers, max_lengths, min_length, length_factor, max_varchar_length, strict_max):
    """
    打印字段分析结果。
    """
    print("\n字段长度分析：")
    for col_name, max_len in zip(headers, max_lengths):
        varchar_len = calc_varchar_length(
            max_len=max_len,
            min_length=min_length,
            length_factor=length_factor,
            max_varchar_length=max_varchar_length,
            strict_max=strict_max,
        )
        print(f"- {col_name}: 原始最大长度={max_len}, 建表类型=VARCHAR({varchar_len})")


def main():
    parser = argparse.ArgumentParser(
        description="CSV 自动建表并导入 MySQL，所有字段使用 VARCHAR"
    )

    parser.add_argument("--csv", required=True, help="CSV 文件路径")
    parser.add_argument("--host", default="127.0.0.1", help="MySQL 地址")
    parser.add_argument("--port", type=int, default=3306, help="MySQL 端口")
    parser.add_argument("--user", default="root", help="MySQL 用户名")
    parser.add_argument("--password", default="", help="MySQL 密码")
    parser.add_argument("--database", required=True, help="MySQL 数据库名")
    parser.add_argument("--table", required=True, help="目标表名")

    parser.add_argument("--encoding", default="utf-8-sig", help="CSV 编码，常用 utf-8-sig 或 gbk")
    parser.add_argument("--delimiter", default=",", help="CSV 分隔符，默认英文逗号")
    parser.add_argument("--batch-size", type=int, default=1000, help="批量插入大小")
    parser.add_argument("--drop", action="store_true", help="如果表存在，先删除再创建")
    parser.add_argument("--only-sql", action="store_true", help="只生成建表 SQL，不连接数据库、不导入数据")
    parser.add_argument("--keep-empty-string", action="store_true", help="保留空字符串，不转换为 NULL")

    parser.add_argument("--min-length", type=int, default=20, help="VARCHAR 最小长度")
    parser.add_argument("--length-factor", type=float, default=1.2, help="字段长度冗余倍数")
    parser.add_argument("--max-varchar-length", type=int, default=1000, help="VARCHAR 最大长度")
    parser.add_argument("--strict-max", action="store_true", help="严格按 CSV 最大长度建表，不乘冗余倍数")

    args = parser.parse_args()

    try:
        print("开始分析 CSV...")
        headers, max_lengths, row_count = analyze_csv(args.csv, args.encoding, args.delimiter)

        print(f"CSV 文件：{args.csv}")
        print(f"字段数量：{len(headers)}")
        print(f"数据行数：{row_count}")

        print_column_analysis(
            headers=headers,
            max_lengths=max_lengths,
            min_length=args.min_length,
            length_factor=args.length_factor,
            max_varchar_length=args.max_varchar_length,
            strict_max=args.strict_max,
        )

        create_sql = build_create_table_sql(
            table_name=args.table,
            headers=headers,
            max_lengths=max_lengths,
            min_length=args.min_length,
            length_factor=args.length_factor,
            max_varchar_length=args.max_varchar_length,
            strict_max=args.strict_max,
        )

        print("\n生成建表 SQL：")
        print(create_sql)

        if args.only_sql:
            print("\n当前为 only-sql 模式，不执行建表和导入。")
            return

        print("\n开始连接 MySQL...")
        conn = mysql.connector.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database,
            charset="utf8mb4",
        )

        try:
            print("\n开始创建表...")
            create_table(conn, args.table, create_sql, args.drop)

            print("\n开始导入数据...")
            total = insert_csv(
                conn=conn,
                csv_file=args.csv,
                encoding=args.encoding,
                delimiter=args.delimiter,
                table_name=args.table,
                headers=headers,
                batch_size=args.batch_size,
                empty_as_null=not args.keep_empty_string,
            )

            print("\n导入完成")
            print(f"目标库：{args.database}")
            print(f"目标表：{args.table}")
            print(f"成功导入：{total} 行")

        finally:
            conn.close()

    except UnicodeDecodeError as e:
        print("\n读取 CSV 编码失败。")
        print("建议尝试：--encoding gbk 或 --encoding utf-8-sig")
        print(f"错误信息：{e}")
        sys.exit(1)

    except mysql.connector.Error as e:
        print("\nMySQL 执行失败。")
        print("请检查数据库连接、库名、表名、权限，以及 VARCHAR 字段是否过多过长。")
        print(f"错误信息：{e}")
        sys.exit(1)

    except Exception as e:
        print("\n执行失败。")
        print(f"错误信息：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
