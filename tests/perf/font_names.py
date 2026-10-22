"""수정한 글꼴의 식별 이름을 바꾼다. 원저작권·라이선스·출처 필드는 보존한다."""

# OpenType name: 저작권, 상표, 제작자, 설명, URL, 라이선스는 출처 표기다.
ATTRIBUTION_IDS = {0, 7, 8, 9, 10, 11, 12, 13, 14, 19}


def rename_pretendard(font, family):
    """가족·고유·전체·PostScript 이름과 가변 인스턴스 이름까지 바꾼다."""
    compact = family.replace(" ", "")
    for row in font["name"].names:
        if row.nameID in ATTRIBUTION_IDS:
            continue
        value = row.toUnicode()
        value = value.replace("Pretendard Variable", family)
        value = value.replace("PretendardVariable", compact).replace("Pretendard", compact)
        row.string = value.encode(row.getEncoding())


def reserved_names(font):
    return [(row.nameID, row.toUnicode()) for row in font["name"].names
            if row.nameID not in ATTRIBUTION_IDS and "pretendard" in row.toUnicode().lower()]
