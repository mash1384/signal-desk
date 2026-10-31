"""이용약관 · 개인정보처리방침(2026-10-31, 운영자: 문의 support@delfona.com). 실제로 저장 · 처리하는 것과 같아야 한다 —
회원 DB(worker/migrations/users), 로그인(worker/src/auth.js · oauth.js), 브라우저 저장(df-lang · df-theme · df-my · df-acct)을 바꾸면 여기도 고친다."""
EFFECTIVE = ("October 31, 2026", "2026년 10월 31일")
MAIL = "support@delfona.com"

PRIVACY_KO = """
<section><p>Delfona(이하 '서비스')는 이용자의 개인정보를 소중히 다루며, 서비스에 꼭 필요한 정보만 모으고 목적이 끝나면 바로 지워요. 이 방침은 어떤 정보를 왜 모으고 언제 지우는지 알려 드려요.</p></section>
<section><h2>1. 처리하는 개인정보</h2><ul>
<li><b>이메일로 가입할 때</b> — 이메일 주소, 비밀번호(되돌릴 수 없는 형태로 바꿔 저장하며 원래 비밀번호는 저장하지 않아요)</li>
<li><b>카카오 · 구글로 가입할 때</b> — 그 회사가 주는 회원 식별 번호, 이름(닉네임), 이메일 주소(제공에 동의한 경우)</li>
<li><b>동의 기록</b> — 만 14세 이상 확인, 이용약관 · 개인정보 동의 시각, 마케팅 정보 수신 여부와 시각, 화면 언어</li>
<li><b>서비스를 쓰는 동안 자동으로 생기는 정보</b> — 로그인 유지 기록, 인증번호(되돌릴 수 없는 형태), 반복 시도를 막기 위한 횟수 기록(접속 IP 는 되돌릴 수 없는 형태로 바꿔 짧게만 보관)</li>
</ul><p>휴대폰 번호, 주민등록번호, 결제 정보는 받지 않아요.</p></section>
<section><h2>2. 쓰는 목적</h2><ul>
<li>회원 가입 · 로그인 · 본인 확인, 같은 메일로 여러 계정이 생기지 않게 막기</li>
<li>인증번호 · 비밀번호 재설정 · 보안 알림 메일 보내기</li>
<li>자동 가입 · 무차별 로그인 시도 같은 부정 이용 막기</li>
<li>마케팅 정보 수신에 동의한 경우에만 새 기능 · 이벤트 안내</li>
</ul></section>
<section><h2>3. 보관 기간과 파기</h2><ul>
<li>회원 정보는 <b>탈퇴할 때까지</b> 보관하고, 탈퇴하면 바로 지워요. 카카오 · 구글 연결 정보와 로그인 유지 기록도 함께 지워요.</li>
<li>인증번호는 최대 1시간, 소셜 로그인 처리 중 임시 정보는 몇 분, 반복 시도 횟수 기록은 정해진 시간(최대 하루)이 지나면 지워요.</li>
<li>로그인 유지 기록은 만료되면(최대 180일) 지워요.</li>
</ul></section>
<section><h2>4. 처리를 맡기는 곳(위탁) · 국외 이전</h2>
<p>서비스 운영을 위해 아래 회사에 처리를 맡기며, 이 회사들의 서버는 국외(미국 등)에 있을 수 있어요. 맡긴 목적 밖으로는 쓰이지 않아요.</p><ul>
<li><b>Cloudflare, Inc.</b>(미국) — 서버 · 회원 데이터 저장, 자동 가입 막기(Turnstile)</li>
<li><b>Resend, Inc.</b>(미국) — 인증번호 · 보안 메일 발송(이메일 주소, 메일 내용)</li>
<li><b>카카오 · Google</b> — 이용자가 고른 경우 소셜 로그인(각 회사의 방침을 따름)</li>
</ul><p>개인정보를 다른 곳에 팔거나 제3자에게 제공하지 않아요. 법령에 따라 요구되는 경우만 예외예요.</p></section>
<section><h2>5. 쿠키와 브라우저 저장</h2><ul>
<li><b>로그인 쿠키</b> — 로그인 상태를 유지하는 데만 써요.</li>
<li><b>브라우저에만 저장하는 것</b> — 화면 언어 · 어두운 화면 설정 · '내 자산'에 고른 종목은 이용자 브라우저에만 저장되고 서버로 보내지 않아요.</li>
<li>광고용 추적 쿠키나 기기 추적은 쓰지 않아요. 방문 통계는 합계만 남기고 개인을 알아볼 수 있는 값은 저장하지 않아요.</li>
</ul><p>브라우저 설정에서 쿠키를 지울 수 있어요. 로그인 쿠키를 지우면 다시 로그인해야 해요.</p></section>
<section><h2>6. 이용자의 권리</h2>
<p>언제든 '내 계정' 화면에서 내 정보를 보고, 마케팅 수신을 끄고, 탈퇴할 수 있어요. 열람 · 정정 · 삭제 · 처리 정지를 원하면 아래 메일로 알려 주세요. 늦지 않게 처리하고 결과를 알려 드려요.</p></section>
<section><h2>7. 안전하게 지키는 방법</h2><ul>
<li>비밀번호 · 인증번호는 되돌릴 수 없는 형태로만 저장해요.</li>
<li>모든 연결은 암호화(HTTPS)하고, 회원 데이터에는 꼭 필요한 사람만 접근해요.</li>
<li>같은 메일 · 같은 접속지에서 반복되는 시도는 자동으로 막아요.</li>
</ul></section>
<section><h2>8. 개인정보 보호 문의</h2>
<p>개인정보 보호책임자 · 문의: <a href="mailto:{mail}">{mail}</a></p>
<p>개인정보 침해 신고 · 상담은 개인정보침해신고센터(privacy.kisa.or.kr, 국번 없이 118), 개인정보분쟁조정위원회(kopico.go.kr, 1833-6972)에도 할 수 있어요.</p></section>
<section><h2>9. 바뀔 때</h2><p>이 방침이 바뀌면 시행 7일 전(이용자에게 불리한 변경은 30일 전)에 사이트에 알려 드려요.</p><p>시행일: {eff}</p></section>
"""

PRIVACY_EN = """
<section><p>Delfona ("the service") collects only what it needs to run, and deletes it once the purpose is over. This policy explains what we collect, why, and when we delete it.</p></section>
<section><h2>1. What we collect</h2><ul>
<li><b>Email sign-up</b> — email address and password (stored only as a one-way hash; we never store the password itself)</li>
<li><b>Kakao or Google sign-in</b> — the account ID that provider gives us, your name (nickname), and email address if you agree to share it</li>
<li><b>Consent records</b> — age (14+) confirmation, when you agreed to the terms and this policy, marketing preference and when, display language</li>
<li><b>Created while you use the service</b> — sign-in sessions, verification codes (one-way hashed), attempt counters to stop abuse (your IP address is hashed and kept only briefly)</li>
</ul><p>We do not collect phone numbers, national ID numbers or payment details.</p></section>
<section><h2>2. Why</h2><ul>
<li>Sign-up, sign-in and identity checks; one account per email address</li>
<li>Verification codes, password reset and security emails</li>
<li>Stopping automated sign-ups and brute-force attempts</li>
<li>Product news and events — only if you opted in</li>
</ul></section>
<section><h2>3. Retention and deletion</h2><ul>
<li>Account data is kept <b>until you delete your account</b>, and deleted right away when you do — including linked Kakao/Google IDs and sessions.</li>
<li>Verification codes: at most one hour. Social sign-in hand-off data: a few minutes. Attempt counters: until their window ends (at most a day).</li>
<li>Sessions are deleted when they expire (at most 180 days).</li>
</ul></section>
<section><h2>4. Processors and transfers abroad</h2>
<p>We use these companies to run the service; their servers may be outside Korea (e.g. the United States). They process data only for the purposes below.</p><ul>
<li><b>Cloudflare, Inc.</b> (US) — servers, account storage, bot protection (Turnstile)</li>
<li><b>Resend, Inc.</b> (US) — sending verification and security emails (email address, message)</li>
<li><b>Kakao, Google</b> — social sign-in when you choose it (their own policies apply)</li>
</ul><p>We never sell personal data or give it to third parties, except where the law requires it.</p></section>
<section><h2>5. Cookies and browser storage</h2><ul>
<li><b>Sign-in cookie</b> — used only to keep you signed in.</li>
<li><b>Stored only in your browser</b> — language, dark mode and the assets you pick in "My assets" stay in your browser and are not sent to us.</li>
<li>No advertising cookies or device tracking. Visit statistics are totals only, with nothing that identifies you.</li>
</ul></section>
<section><h2>6. Your rights</h2><p>From the Account page you can view your data, turn off marketing emails and delete your account at any time. For access, correction, deletion or restriction requests, email us below.</p></section>
<section><h2>7. How we protect it</h2><ul><li>Passwords and codes are stored only as one-way hashes.</li><li>All connections use HTTPS; account data is accessible only to those who need it.</li><li>Repeated attempts from the same email or network are blocked automatically.</li></ul></section>
<section><h2>8. Contact</h2><p>Privacy officer and enquiries: <a href="mailto:{mail}">{mail}</a></p></section>
<section><h2>9. Changes</h2><p>We announce changes on the site 7 days before they take effect (30 days for changes that reduce your rights).</p><p>Effective: {eff}</p></section>
"""

TERMS_KO = """
<section><h2>1. 서비스</h2><p>Delfona 는 크립토 · 미국 주식 · 경제 · AI · 세계정세 소식을 모아 한 줄로 정리하고, 호재 · 악재를 판정하고, 소식 뒤 가격 움직임과 시장 브리핑을 보여 주는 정보 서비스예요.</p></section>
<section><h2>2. 투자 조언이 아니에요</h2><p>서비스의 판정 · 요약 · 브리핑은 AI 와 프로그램이 공개 정보로 만든 참고 자료이며, 틀릴 수 있어요. 특정 자산을 사거나 팔라는 권유가 아니고, 지난 기록이 앞으로도 같다는 뜻도 아니에요. 투자 판단과 그 결과는 이용자에게 있어요.</p></section>
<section><h2>3. 회원</h2><ul>
<li>만 14세 이상이면 이메일 또는 카카오 · 구글 계정으로 가입할 수 있어요.</li>
<li>한 메일 주소로는 한 계정만 만들 수 있어요. 계정과 비밀번호는 본인이 안전하게 지켜 주세요.</li>
<li>회원이 아니어도 대부분의 화면을 볼 수 있어요.</li>
</ul></section>
<section><h2>4. 하면 안 되는 것</h2><ul>
<li>자동 프로그램으로 대량 가입하거나 화면 · 자료를 대량으로 수집하는 행동</li>
<li>서비스를 방해하거나 보안을 뚫으려는 행동, 다른 사람인 척하는 행동</li>
<li>서비스의 글 · 화면을 출처 없이 대량으로 다시 퍼뜨리거나 팔기</li>
</ul><p>이를 어기면 미리 알리고(급한 경우 나중에 알리고) 이용을 멈추거나 계정을 지울 수 있어요.</p></section>
<section><h2>5. 콘텐츠</h2><p>소식 원문의 권리는 각 매체에 있으며, 서비스는 제목 · 짧은 요약 · 링크만 보여 줘요. 서비스가 만든 요약 · 판정 · 브리핑 · 화면의 권리는 Delfona 에 있어요. 개인적으로 보고 출처와 함께 짧게 인용하는 것은 괜찮아요.</p></section>
<section><h2>6. 서비스 변경 · 중단</h2><p>서비스 내용은 더 나아지기 위해 바뀌거나, 점검 · 장애로 잠시 멈출 수 있어요. 중요한 변경은 미리 알려 드려요. 유료 서비스를 시작하면 가격과 조건을 따로 알리고 동의를 받아요.</p></section>
<section><h2>7. 책임</h2><p>서비스는 정보의 정확성과 제때 제공을 위해 노력하지만, 외부 자료의 오류 · 지연이나 AI 판정의 오류로 생긴 투자 손실은 책임지지 않아요. 다만 서비스의 고의나 중대한 잘못으로 생긴 손해는 법에 따라 책임져요.</p></section>
<section><h2>8. 탈퇴</h2><p>'내 계정' 화면에서 언제든 탈퇴할 수 있고, 탈퇴하면 계정 정보는 바로 지워져요(<a href="{B}privacy/">개인정보처리방침</a>).</p></section>
<section><h2>9. 문의 · 약관 변경</h2><p>문의: <a href="mailto:{mail}">{mail}</a></p><p>약관이 바뀌면 시행 7일 전(이용자에게 불리한 변경은 30일 전)에 사이트에 알려 드려요. 이 약관은 대한민국 법을 따라요.</p><p>시행일: {eff}</p></section>
"""

TERMS_EN = """
<section><h2>1. The service</h2><p>Delfona collects news on crypto, US stocks, the economy, AI and world affairs, summarizes each story in one line, labels it bullish or bearish, and shows the price moves after it along with market briefings.</p></section>
<section><h2>2. Not investment advice</h2><p>Labels, summaries and briefings are reference material produced by AI and programs from public information, and they can be wrong. They are not a recommendation to buy or sell anything, and past records do not mean the future will repeat. Investment decisions and their results are yours.</p></section>
<section><h2>3. Accounts</h2><ul><li>Anyone 14 or older can sign up with an email address or a Kakao or Google account.</li><li>One account per email address. Keep your credentials safe.</li><li>Most screens are available without an account.</li></ul></section>
<section><h2>4. Not allowed</h2><ul><li>Automated mass sign-ups or scraping of screens and data</li><li>Disrupting the service, attempting to break its security, or impersonating others</li><li>Republishing or selling the service's content in bulk without attribution</li></ul><p>We may suspend or delete accounts that do this, with notice (afterwards in urgent cases).</p></section>
<section><h2>5. Content</h2><p>Original articles belong to their publishers; we show only headlines, short summaries and links. Summaries, labels, briefings and screens made by the service belong to Delfona. Personal viewing and short quotes with attribution are fine.</p></section>
<section><h2>6. Changes and interruptions</h2><p>The service may change to improve, or pause for maintenance or outages. We announce important changes in advance. If paid plans launch, prices and terms will be announced separately and require your agreement.</p></section>
<section><h2>7. Liability</h2><p>We work to keep information accurate and timely, but we are not liable for investment losses caused by errors or delays in external data or by AI labels. We remain liable as the law requires for damage caused by our intent or gross negligence.</p></section>
<section><h2>8. Leaving</h2><p>Delete your account any time from the Account page; your account data is deleted right away (<a href="{B}privacy/">Privacy policy</a>).</p></section>
<section><h2>9. Contact and changes to these terms</h2><p>Contact: <a href="mailto:{mail}">{mail}</a></p><p>We announce changes 7 days before they take effect (30 days for changes that reduce your rights). These terms are governed by the laws of the Republic of Korea.</p><p>Effective: {eff}</p></section>
"""


def body(kind, B):
    ko, en = (PRIVACY_KO, PRIVACY_EN) if kind == "privacy" else (TERMS_KO, TERMS_EN)
    t = ("Privacy policy", "개인정보처리방침") if kind == "privacy" else ("Terms of service", "이용약관")
    fill = lambda s, eff: s.replace("{mail}", MAIL).replace("{eff}", eff).replace("{B}", B)
    return ('<div class="wrap st lg">\n  <header><h1><span data-l="en">%s</span><span data-l="ko">%s</span></h1>'
            '<p class="eff"><span data-l="en">Effective %s</span><span data-l="ko">시행일 %s</span></p></header>\n'
            '  <div data-l="en">%s</div>\n  <div data-l="ko">%s</div>\n</div>') % (t[0], t[1], EFFECTIVE[0], EFFECTIVE[1], fill(en, EFFECTIVE[0]), fill(ko, EFFECTIVE[1]))
