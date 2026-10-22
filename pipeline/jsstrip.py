"""배포본 JS에서 '줄 전체가 // 주석'인 줄만 뺀다(소스는 그대로). 페이지 무게 예산 안에서 기능을 늘리려고(5회차).

안전: 문자열 · 템플릿 리터럴(${} 중첩) · 블록 주석 · 정규식 리터럴 상태를 따라가며, 줄이 시작될 때 '보통 코드' 상태이고
그 줄이 공백 + // 로만 이루어질 때만 지운다. 템플릿 안의 // 줄은 그대로다.
검증: tests/js/strip_check.mjs 가 원본과 결과의 토큰(주석 제외)이 같은지 JS 파서로 확인한다(CI lint 작업).
"""
import re

_REGEX_BEFORE = set('(,=:[!&|?{};+-*%<>~^')
_REGEX_WORDS = {'return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void', 'throw', 'case', 'do', 'else', 'yield', 'await'}


def strip_line_comments(src):
    lines = src.split('\n')
    keep = []
    stack = []          # 'T' = 템플릿 리터럴 안, 'E' = 템플릿 안 ${ } 코드(중괄호 깊이는 숫자로)
    block = False
    prev = ''           # 마지막 의미 있는 글자(정규식 판단용)
    word = ''           # 마지막 낱말
    for line in lines:
        normal_start = not block and (not stack or stack[-1] != 'T')
        if normal_start and line.strip().startswith('//'):
            continue    # 줄 전체 주석: 버린다
        keep.append(line)
        i, n = 0, len(line)
        while i < n:
            c = line[i]
            if block:
                j = line.find('*/', i)
                if j < 0:
                    i = n
                    break
                block, i = False, j + 2
                continue
            if stack and stack[-1] == 'T':
                if c == '\\':
                    i += 2
                    continue
                if c == '`':
                    stack.pop(); prev, word = '`', ''; i += 1
                    continue
                if line.startswith('${', i):
                    stack.append(1); i += 2
                    continue
                i += 1
                continue
            # 보통 코드(또는 ${ } 안)
            if line.startswith('//', i):
                break
            if line.startswith('/*', i):
                block, i = True, i + 2
                continue
            if c in '"\'':
                j = i + 1
                while j < n and line[j] != c:
                    j += 2 if line[j] == '\\' else 1
                i, prev, word = j + 1, c, ''
                continue
            if c == '`':
                stack.append('T'); i += 1
                continue
            if c == '/' and (prev == '' or prev in _REGEX_BEFORE or word in _REGEX_WORDS):
                j, cls = i + 1, False
                while j < n:
                    d = line[j]
                    if d == '\\':
                        j += 2
                        continue
                    if d == '[':
                        cls = True
                    elif d == ']':
                        cls = False
                    elif d == '/' and not cls:
                        break
                    j += 1
                j += 1
                while j < n and line[j].isalpha():
                    j += 1
                i, prev, word = j, 'r', ''
                continue
            if stack and isinstance(stack[-1], int):
                if c == '{':
                    stack[-1] += 1
                elif c == '}':
                    if stack[-1] == 1:
                        stack.pop(); i += 1; prev, word = '}', ''
                        continue
                    stack[-1] -= 1
            if c.isspace():
                i += 1
                continue
            m = re.match(r'[A-Za-z_$][\w$]*', line[i:])
            if m:
                word, prev = m.group(0), 'w'
                i += len(word)
                continue
            prev, word = c, ''
            i += 1
    return '\n'.join(keep)
