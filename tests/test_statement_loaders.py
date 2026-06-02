from pathlib import Path

from corp_stat_autofiller.loaders.bs_csv_loader import load_bs_amounts
from corp_stat_autofiller.loaders.pl_csv_loader import load_pl_amounts


def test_pl_loader_sums_quarter_months_and_reads_unnamed_total_column(tmp_path: Path):
    csv_path = tmp_path / "pl.csv"
    csv_path.write_text(
        ",勘定科目,補助科目,1月,2月,3月,合計\n"
        "売上高合計,,,1000000,2000000,3000000,6000000\n",
        encoding="utf-8",
    )

    amounts = load_pl_amounts(csv_path, [1, 2, 3])

    assert amounts[0].account == "売上高合計"
    assert amounts[0].amount == 6_000_000


def test_bs_loader_uses_quarter_end_month(tmp_path: Path):
    csv_path = tmp_path / "bs.csv"
    csv_path.write_text(
        ",勘定科目,補助科目,1月,2月,3月\n"
        "現金及び預金合計,,,1000000,2000000,3000000\n",
        encoding="utf-8",
    )

    amounts = load_bs_amounts(csv_path, [1, 2, 3])

    assert amounts[0].account == "現金及び預金合計"
    assert amounts[0].amount == 3_000_000
