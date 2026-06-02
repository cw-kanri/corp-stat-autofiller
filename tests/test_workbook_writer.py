from openpyxl import Workbook

from corp_stat_autofiller.writers.workbook_writer import resolve_writable_cell


def test_resolve_writable_cell_returns_merged_range_anchor():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.merge_cells("B21:B29")

    assert resolve_writable_cell(worksheet, "B27") == "B21"
    assert resolve_writable_cell(worksheet, "K21") == "K21"

