(()=>{try{
const F=document.fonts;if(!F||!window.FontFace)return;
const P={h:0.8643,l:0.4635,a:0.950,d:0.240};
const H="라물재스스갑사평재다성격제급마테을트다신시전물비습약금경파선기호러하목라한립저재일새스함테식코황소술국군산장자월용이과간했조증판비판러공악탈피집을신리조싱사중운합를코라월용이리월보증장침없기처승항상은승는요만름간승높약청해기시물당치전보리해처값물하표아변균예일월크솔드러미반를확로이막코이무호요기간며이파소스간다고진위보",L="D1btaByaU.n wTh0-uaICtpe.-ouTo ot41i iiht8 oaok ta1 %t nlc alsetkarsdn sfwgaoiiseg ewr uil1 oiersmercn6heani lidbs40lec g9cn tmo mnt%1ms 5s 7ghma, hsnrt rar 1  tlw.esC im4taMia ehw  ee0cacaey36r0J8eb3RV 'eeT' ii bBnit5sC t ltnNfa eB w e sro";
const c=document.createElement('canvas').getContext('2d'),w=(f,s)=>{c.font='100px '+f;return c.measureText(s).width/s.length/100};
const has=n=>w('"'+n+'",monospace',H+L)!==w('monospace',H+L)||w('"'+n+'",serif',H+L)!==w('serif',H+L);
const C={'Malgun Gothic':['Malgun Gothic','MalgunGothic','MalgunGothicRegular'],'Apple SD Gothic Neo':['Apple SD Gothic Neo Regular','AppleSDGothicNeo-Regular'],
'Noto Sans KR':['Noto Sans KR Regular','NotoSansKR-Regular','Noto Sans KR'],'Noto Sans CJK KR':['Noto Sans CJK KR Regular','NotoSansCJKkr-Regular','Noto Sans CJK KR'],
'Source Han Sans K':['Source Han Sans K Regular','SourceHanSansK-Regular'],'NanumGothic':['NanumGothic','NanumGothicRegular'],
'WenQuanYi Zen Hei':['WenQuanYi Zen Hei','WenQuanYiZenHei','WenQuanYi Zen Hei Regular'],'Noto Sans CJK JP':['Noto Sans CJK JP Regular','NotoSansCJKjp-Regular','Noto Sans CJK JP']};
const N=Object.keys(C).find(has);
if(!N)return;
const ko=document.documentElement.lang==='ko',r=ko?P.h/w('"'+N+'"',H):P.l/w('"'+N+'"',L);
if(!(r>0.5&&r<2))return;
const pc=v=>(v*100).toFixed(2)+'%';
const f=new FontFace('PF Fallback',C[N].map(x=>'local("'+x+'")').join(','),{display:'swap',sizeAdjust:pc(r),ascentOverride:pc(P.a/r),descentOverride:pc(P.d/r),lineGapOverride:'0%'});
F.add(f);document.documentElement.dataset.pf=N;f.load().then(()=>{document.documentElement.dataset.pfs='loaded'},()=>{document.documentElement.dataset.pfs='error';F.delete(f)});
}catch(e){}})();
