# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Rayk Kretzschmar
#
# The MIT grant covers the code in this file -- the market/SELL layer and the scheduler.
# It does NOT cover the base85 `_TRACE` field plan below, which is the shared public meta
# line reconstructed from public competition replays and is not the author's to license.
# See NOTICE, and the "Provenance" section of the dataset description.
"""Closer Cleo -- tier 9 of the Kaggriculture reference ladder.

Meta field plan, sells reordered in place so buys stay funded.

STRATEGY
Same meta field plan, but the SELL layer only reorders within the market slots the plan already used for selling. Nothing is moved into a slot that was holding a purchase.

WHAT THIS TIER TEACHES
The subtlest lesson in the dataset, and the most expensive one to learn the hard way. Sells fund the buys that follow them in the same queue; hoist the sells out of their original slots and a BUY_PRODUCT WHEAT later in the turn fails on a near-zero balance, animals go unfed, and the farm quietly loses far more than the reordering gained.

FIELD PLAN -- READ THIS BEFORE REUSING
This agent does not use an original field plan. It executes the shared public
meta line: `scripts/cross_team_identity.py` over 530 downloaded replays finds
identical 712-turn farmer/hand sequences played by large groups of unrelated
teams -- one group of 29, another of 15, another of 8, with 104 distinct teams
appearing in at least one shared plan. No single team is credited because the
line demonstrably belongs to none of them.

What is the author's own, and what separates tiers 6-9 from each other, is the
market layer: which product takes the earliest slot in the order queue, when to
hold, and when to liquidate. Tiers 6-9 bank within ~1% of each other against the
baseline yet separate cleanly head-to-head, which is the whole point.

Measured end-of-season bank: about 186,198 coins against the built-in
`starter` baseline over a 720-turn season.

This file is self-contained. Rename it to `main.py` and it is a valid
competition submission; or import it and call `agent(obs)` directly.

Part of the Kaggriculture Reference Agents dataset:
https://www.kaggle.com/datasets/raykkretzschmar/kaggriculture-reference-agents
"""

import base64
import copy
import json
import zlib

_TRACE = json.loads(zlib.decompress(base64.b85decode(
    'c-rk<%Whm*a{QHs*1b?YNKxLgr5Z~ZwkS}P3*$zi(SXM=V2l@S?+pLDDUnt86`2u{=M>c%%t|G)c<*_i%*e>dU;g*SzyJ38-~Rghi+}pzmlq$eKYe;}`0<Aq|MA;@{o8+k`O%mE{Oz~j|MRc^^W}fPy!h$!Uw-{~cl-A9oBJ0JzuLdsU4Qwo-5d`8_u~(fhkdxcyMLEI?bGh&X8f4V)x$R)U-D_UdprKs<>EI#?{02CJbYNKzy9jo`@7u>>(iHqU4MB0^Yzy@yt&;!{IdqX`SfnL`}p;Di$3mmpYEq!d>F*{Z~pxG<M7DU*GC?|IU1Mo50`($#%iUtX7sk<9mgK6<_#Ks{OR-io43C{tcd&1Uj|HE2%uFTZ>~Sw4-+<P-|RKhb`DRSH7@GP!@J(>j-x0H;c>FHp6svhcXx~Fp1d-g>Znt1uF>c=w-l^|$2Wng{Si*mxF3(7dN(p(7^A&$9O1{ger(ZkD!_hvmT4co^-o_8q}hmpAwEyzcGutp0+Tt+em=1CzkQDOW|KJ^;Ky(FZq#vb@cM&onvZAq&9S(O@w|?YnB%V>AG@6FWMZWgWHe9kyuj0lrc7HF!}$ZBy!=RB(rHZ5pUl5^*3n&l>@~W_FHRQD*HLR3+R@kzFGxpr{4?eC-Ny5=eU;8W{VW*H;n(%yoIN5Ru<oxK59gUW6MkYZfVNfab|?;lw#0VJ?SgFj(K(;@1o%v`=?HHq?Ib+jsN>fRw=6zmAAe6CjBe7@@EpAWnZnB#+}_;m-rWECr`_HC`<wUwy0pyjH;8eD{-|)Mo-C@-bC%OJEbmXZpO>>W7!Tknfdv8l@26)AR?X>~aR=I4xP=ZtFj~@l4hPbx1GzP(H+QX>WW(An`g+n^M%VJ_)@r|@-`?GRoZnQ#G0@>~9}h~;OXFOZ5!$1F;O2gB!+R!s=pW5(w4cuO*u^opmC)eeke(yL7c$r@nLoKLhprV9M$pZ*C3*mEBW?&m+`={$p-IXft+}OW8dCpWZ#9~VW&29bG#_~A0TP%}@;9&@;C3Ki{cvh~EPvc$>A`%&N%N&~fd=!~v_!VoyX(7uQTl)eeV9%-u_mU3h99^7)aIUxe)OuTKd}HPv>i-<;+747{f@12#tjn{Onh*SZNrEo!hS&nk+!V9aNr4#H?FyA@RJGJuR(CLs2goM@wuhll-oq&+IucrYeVDsb%UxaOlICPs_iD<W16+)n|AK)>DY7l<Dwb;wr7hirrR6vOs^Y!v@4T~P<)Sb5#kQPI9)xC6W#0R6jZGhawQ}^An~)xQh|e*j&fnGU_(6^Tk#5^O9h&J#CmG5Wr@AHY(uY?K*XxWR@=l!BYG=wI0Bn(<JfFMT;c>3k7hVqc7>6VY;wGHkl7VtGG^Q-@C{}_TPZd+H|v&Uy2`uwYz_|`Ky*36Q?@qiZ!jXtGdkP6r?w?}QM5$Izj+v-yW9KIru-gJzjNAyi2+*O(Qv!La2I{$cp^XD-(By2+TGp#1-}+e(r9ZNc4*nIhn@5dQsefA*O&Gh!ubuRsRulZEeF-Y%m*G>TNOym01lC@MMBRN^9Y*dixpRATa*1WEU%>%&<$T4{WL_$405JnSxx9=$U0(6NIxHQpd+zD`_3&kfV!F=`h)vUYnQG;mQMcQ=6TBBIoOLX#s^)Yi)Jv9Le{X?a|>;9v2PCF4*2xV&8=Wl_Bj?95?Qigah&~Zwk_ld>RntKW$8+4yb$^Tr7)c)unqdWv1EI>FR9FKe=``H+u$ax#|;GvVQ+eUgfb(@*^hd~qdB7Q9Sxn)e#(ErIxbUm*bXMXWf}*N&o2CuU?pG|(<LexkyO|(&7^^Efi^x0^vjD4roAmvvC;)qAR6SEi`d_Y7xb>$PvOL9SSRSfAmIFh>e)zU$t+(z?Iul#1=b{fYf5CM)+s!6)~*4Hta5ia&YtM9+#HH|yN=ORdUV$^>!}$l<++52ca~yv0l(Yl9!okjI_YxLd?WM<CKIJS(zZWJR7UStzDM34j0em@1}(s86<!k@LlC}YoSIblJJpuk-`;*%i>sHyIhqVf!qO6&H}cCy&8a2Mkc0X7>xWDGts=xRdIxj9i6M@zSd{n@f3Kcb#G1Z{S>laLVg?8a?bnAaH)?ryQ-pRIr5$yIZ@9c)ZSDYSCCp-m^FiD?2TEL|Dh5j%q%?vbL2gFO&@CKh>EfO8f@Wc6EJ}h;z?9f^mSjqV#|(=)bU@I?jeC_PsKQrtWovMcCr#vKdIA=xzODnS(2pu4;Yba@{wU(VVb@e(26j-EPz7oTG26z)uxE{69&(`WQ7l*kF%0Au#DW{3GwnIzq@sa@%R3RZ$N-@_HnT{*mN|HiZE`#pUW;k&F>6qqpM<d3FtNc2y;h~hPOXaO5e~OC>G~y-nta5&Sch4i1lQU2#Ub)b1)FpPrU<MMRe*5iiVTjg3i*dIf};FQhdd1^pO)#4oHKYiTuH;Phfhg-s$=YH^uFMF8ooRF#NDLsSjoif#g=UNr@_w^sKWsAx?u<0A5EQD#`E?ZmP#}*99TvP3;(dWBb(Nvj|kTcyk+iZWoZySd11)$jkguSc)DbH5$XnM0yBdv<}6mW$+j1b#dTrO?swvBgo9G&ud;zsiN37_2R+eeu?zK)6laSJ3Bp268@`@NoohCDTM4dnf~T}BAo4yuhGn@#;^sqFG6yQl5n9Hj%7$Nv5*zn<I!+oJw!bPA^e#s>;PA89xO*;*O7schP3HRrDf@yiTaB)(>q(ADUj(uAtr<z`&{H>%&78+nxuXz8I$dx-zrXqOQ&|G+&@m2bbQ>%lPw&WKMLhl0YMl!)3ISRMQdm_Im=GAT_#ngx5jqJ*7DEslk+lLtJd5%KYl&vSqKReT1ujPTwr=fm2G)s3Elo_lAHBrIoYYJJm*6@E7%HcHLo2S<vZ#aXyu>k0ap?A?Ty?@o;-c^1o@=So$tO6i?y#RHtu-K3?^G2EU3toxfgI?YI)BUky0fFprm~eP6bJ3v7%TTA?^{=NCNU9S>AAjMDZzy<Rz2MX#-N3R$DDp>?~<4~iRLh`R#rzz*ctGoR)Z7K#$v1JZ2FWt8DgXZ+DTn83uq@4*;wd3*kLtkdS88>**!cQ#%MFHE}x_cDNsjpn1-gZ)G~DoD{3TLL*~M)2J)<$g|D6`fx)B@L=cN|WFH-L*|xJ4t$0;LBWxOgOoXvK%2F)wYyD*7ChjK;j_1)jg@?_p8~J9N=MrpfnzNAWpz!01T12B}I}<}9cMP>4a|kcX^HtihE<X%;fK_0HMw=%@R#VC|7Q__#lBiL=eh?l=zFVsC+H-)Fn&gx@FLizBd~;xn+OiDs*hhp&Pt(R;{{d{q0tJy`0Evg5dpi&fSZ{L3!yIR|+x5Z1<a9SM9#5Tm0bw490_m}BLwvbk;tU~fsKVh9AYIlq<9?p9)Csm=$|-l$x+CstpcR`ViZs<nK#`E8O`?BP*A{;vVY?KlvP@SYlSDwm1EN^3%T|<2@U2@V9r9129-*1Cdb#Y~acnW}(bn>e0o1D;L@X5-ee(X|?0Ob0pQ^}X6IrJxR8-D8iQpr%;6z1mjv+u-Jt}@M|4#mE1N6DbT-l5BWCk7I>M#)aDrn)!k`6F76*YMm4-gH<3mI6X-ZV5WsaZd<Ac-8WWD=01yUcEk{xnzf64HU{laa^FC4oC63M}#RY@ar7EHplbbqjy33WvCA#}@~eY7d*o3N3`C*`BzDyPMk&C$ixj_zAg&r@u-_lA|Zn{)|2fDt){o&~YG7W}VHMmEtuLw3l}SVZ9AsMi8Gk4(n~*4hUM4%Y;n7%TVFPc7B$5MFLvzVq$O-0c0B^^GmcLVlL9)gLH!pUw_n`cyqg~mjcu%DF1VG0MR4LoZLXx5EFbDr+a*^<x;m<@Tsws8%k#e_ZG*c2mn1tChHfWzDxmJh-nsbO3$3d&!DVJcMT~uCU(VLmU~b6>k9d81lx>r8=lTwIl(JK)_FpNOHd+aB1?=5u;~%+K~(%t_5j@8h-yR#@+1y3&-JP}o`HKMB#()Zk>FN!fV^5;*;NeIrB4Mm52nbh^T>as-m+SiwPx3w=iy+%>lTr)6sXMqv{b%~$yQFXpIY3EQ`1PuM@d-T@jStBS+!``3F7zAG^YWtoPFG>q##7DuoAAVPo@&hdL#r`N}Jp=p>hU7noD3=cPWFmQ!N1&epIvx&XKHP?HXaQAv812XB7v67<HG2{(H=vjs32WVAX|I;piF)z?z=?QcFnGtZ(Ini!!z7QZ$%^XCb{nQVt>VDCe2-oi5eXp-&CB4vmtZJ;$#vt<4Y&mALvsn50Q)CYTCUan>?4TF8ea^?1~Fv`>nwtWO!CrSvoOnDvn+As+jH4Q9?&e0Hd9)@g;QZfI8&G+~KeuEqnCR#Ox6FxP6%;Z;IjBJP|EFY8Lq*p>psy&U&zP@TpZwB=Yv&YEPR4R)o$eC0}+jy255KVf7ot#Sfk6Fyetfn9x{Jg{03P^TiuTIT2kkT+_8TugM4Cs<WkBRa2ngpT~WN3K84;<6k!>&vuQ$s#ArPCtyQU||mh`)qID|1)Q<`AsJk8xigS%~Cyq1w|BH%NT0lkUKbF%YmiRTH4F1-NUb4y|7L<Qvi9oltSnx5(MK2X)JJ>qxijJPP_R=NZ$?(9NG_9VQJ|OoooFehrFmRVFN02AoO*MRtigxFXV}wnpI{x<;=*m-fcpibZd~vdHHlPo-Q0y12{+6g@R)xK~-(NR;mCHZYj%+$>h43XTN&c4ftj)&V>xjB_JCWhzTK<u4$I8pGI4g5_E+01N#8-kph{ay!fx?9}ApC;!g?^#oaWfQxpL@$mnqBFE!ngc2*v&<&mTK=&u>eq>s}sAdT2X_eucQ9DY5YE7I~kYSZ$1rQ4X9v302^_?pO30&-A0<ww?TOdM`qn4(U|3AOgF+M?Wev>mMTykl>1MVKNFV^Uku-WK8&V}dY&1~s(RWQyYa7;GT()Uz{)C^K3{v`n;GxN4P@>dJOXYKeq|cxfbPWK)?o{0g>wyAJKjSDfA1ifj}o)57wO-mJH#{o1Up0W)yJQ3bo`m`ExoRTRK2X`x}n(}LKYgk1BL8Ie937iX^nHz`ylE>oDg_XsU*dfsg4aHVGvrjE@@HCRg21Wnr<>QylXoHzXx2h}So$;7nHabF_rkPCV>=^Wwch;V$!oZbea6E*$v3NfSQ%GS8ZDMQc-4S-}pt`K;0$FGfQFnofyZ^B8aL?Zrh90PO^dx<irunoWm$bpoWmy%4u*8x5gAGZXF%_*A9IH-%llJG8ZZaLKhhN#nYr*(7GO)zt??}<(gK&$H+>Se50l0MAcI7CM%1b|5@R`n)Z#LEiS7CuU6M3Bpnx)FH_aEWk|!h-5?dGJ@Tkp-U<Kl18Nld+K~H<yRD<t`H}tB6bYg-?>ood|z|2ADDX)s=^(om!`{im|EXto@;#TG&+2-3VL|cF#yBw-eD700!cVki{;wm`H1*_l`LclT{&{;a>h$9}9#n2#QE%7-AdQT$b`;(7Q{`Hr6TM*1@f#oy8^M1aa@;8(CVf`5hwz-<4%cU@Ls?vV_JMsi1?ei@_|29!m6(iUXhQtzvZ)$^IKS0t~2R=YvL_t(+Oqv!D1QlckMl50s+ZRY<oneZs{rmTur>u>jLIOqU2Ci3?L>HLt6tk~MrfMuBp1VV5#cYfLSX1abgT9R%?N8ej-V0%Wh!r_rU4K&@FbqRWx=v@N(vI;9sFXE%nFdQ&qaC5u6@WoJ)<{#LHsTc4VBKS^SSkyo^QyQMNC%Q<o8<b3!E*m0!|2~oB@Jxs4cH(iPO-l2)tBI{iXw~!E~yK7>LorVutx{%hNO1&upLeV4=&Zf7cV8Kd)=O%PDt=tka6mCK}25RXZnB{9uzHi(uNv+1l_^7)Xw3MB2uxb4yX)=P9q$lqfW$<#gjx-0t+CeMdQQ;7H`sw2uPgJn-8Bru*H|0w84as%_+~>lhBs-}0$`5h~Cu=D$qRuo@0(2CG?Fdy_)P-gBq>Mu0p3Z%r!Ozo+B<n}3N&%8v<OFk?v~r@pjCDh=gftceR?!4NL|4IV78#$NHC(D!C1(k-w7}&OIL3=E6sAs|a5OxsYZWP(*;B#8j4EjzfU?)m36ur4hfts>gGIKw@<mIAQUMZM`?RN8))hm+Qa}+|`$UNeketqfkmbHD<jW>0%zT;IK|$yuu(D5qivw*BWCW#YM6C_(Er_d@7S{8y*%re!#;R4f^6e%J23Hf%H;$)l1knMXz)u5CP2~b|r9x;%M?^jaqRlz<rRsGY5GdQ$L2-A+4J#8|iuEJtnyH27Tf{f0*cWw}7E4H=P4%1sxCwaD1<5vo1JJboCFm2bUX|U<(weI{5&=tGIKz5K<f^h*LtL4Nkx<AP$kTlypo9=znidz<bXI6n8l5*pqvjOLPUJ@6Ccv>cRV5jnA8AFV5`zUo9^1k$$aA8U@;QX2lbTzz=4+tUfZ8x(A|9qifhl75Cvh36UviZxv~=|1WGpAUH}+`-v<Qe)Av-n_NA)u9GOFejgqmyj^k<5l3qd=ha?dlNV7Vz$<c4iKWw^EAU}jGvJjN=KWfo;Gkcsk6px|TV8#O5n*KccNNE1OqqB1Ndd=~~*uo*bJf_B7tLXQ~`oMo&_5VIaI&P#t<uj4@&j7D(+XcM$F7kWMc0gseB&f&_)PVfgf*VFIEO)L`SNW{JoW9FO&O{9fK=`m5FmvbFpOgRk?+R?~qm~a%C>E|hd@=QmxVJ28Y1O^bD=w^M;)yt^{V#vKjw~GW-mDmr|G9%jPjMumT9DJt^uC^!u1z|XPZ5jlTC4$l#?Z8pP0JLSgT+tBGGbHYf>~n+U>`9%%=vECP9=KQjDWX(5q~t=IKb%J2AYvgF-D(r`CfkapQa1^!w>6y*h4)w@Ltx*Yak$BKBo^)yLeo74xPc?DD!&8{m|a9RFZD8o5nq}`+k+H^$wJcV^>L=uyrm*Z?^4Okl%XnPKvco(S!?@AJv}Sn#W+to<b@C{j(Y)f?3-mtULIT=WUms0_B;1ej<mJGH@fT-D{~J2Xm0JbHP+)<kTVWK3=0FL&|m?6uxxZoMM?|vSLcFBUy-`B5}hd{w=^S6%!1-y*7D;Po1qP9vIMV$T|k&y4ID*EjHiHIPBwChAH;%hEEwYLZfXk0_B*No<!AT_`-AT42#OF$9Ov2{I;Y$xWn|UL8Mq)8APVD9aB;bk*$s7?H7|?sfn*&e;$+PBhO`XpEG>Gk^K9sy9BHAo*QMpQK6DX0a%7kC-PU90KdBKZ_jx7SOp;(-YcQu!?<pC2Bnuh4_R`hSoF7nj;Yn<p$?lOHK*r;AZ$!kHQ6%>T1$&4s<V9TOp_sPD=j5Xx1L^d8PPQ5mncRJXcuIK9ZzY};>_P2x<Mb?YtIXSf{*=Z-HFQypZgcn^nOljdSB=c2B3MWVi^|dPZuTp#CM%k&(q<~Gr6l!r5RclM3JaX>HM*38E_BcBV^|0!5}`0m#^#|_bVjBHZ?jW`swvW+720mh5R3f|8Zu;4CV&H49~iI;8ye*p<U%%>{pbb{!*#^lM@d6)0`h%8EAkXbgQ%T;W#hKZ(6@rKlx3t7HY^~|&~}SGc^EsjvhpPD5|+ek)~pHliV<**&RMj>(FSpI_t>Et6VvGSCi`l%(dqWEg9;`Tq;njscu;kZR8|(NA|*sl@-%mMHxT^SkWV7MINAn8j!xlQF{Q2uW*|e3g96TGu<3uWU~{mbs3ImS6Tnx$^NoFv?AG9@MHSZO3>Jk@opW&=Xzmi#xGF%zxedk)8bqf>d(2HWL}zj~^2E|5<RF0;DPJ!-X()$@n3kB_C60I5!h{6iO0tqG*@!bD{yO~gAtRWfU*jhQNyrm+du)CFy=Z@Nk*Z5k#)*~#ycFRzg&Q`T(e3%bwv^4t33Z`Eh0aJ)*e%zquY+qW3<D3rn9_i(uEb|-ZLy&WWz~t&@tn54_%h2?w_AYfy3jV56hYSGGs+k!=`2KgoJ*j>#h;aZYKlCE^}}o#ozx@eo1%dO&%rmUauEX%G8x7!>h0zv<i|NDCq9SYEgnQfP8suCv1jTHaa3nxS5vN$AhpqURvv?^d1_Ya<-y$iy!uRt4hA+!iMZL2alIFA0nU}>_r5CbS3sfndF2;=O%M@TS!=7VEMSCYum;#1@&#VtI=mdyEC9*HE`T3Fp=r*GE82`LnZ_HxXk)m+iPW%JMTO);G~Sp*yCN0$3I`x!<?%wuWvwqm!7Y;}bBs_!Ld)VjsY&llQj1fx@Lm<HS~)UT-e+whT2VxRWh|C?g9KTG&0X3vlRyONw@q-qgrM8{yQHWYwJ5hn>A|fhu~mT3R()mE)J$qtHF9t3Tsb%%gfel5qK%7qWHTA@xStH-Fg>K>GbmIBjTfc95%UAh1|Of1R0P6^3_bmc<c;Dfm|cNS^w>~%Wk`-H&FAe>t`Cl-kyMN<EvDkCvLBX9KUmOk4M*cG*j06*F0}lao=LQFW5A|L%>u*Mya$A3&Acrt$|LL|RcXgeBs0qF?peYa$tZF2VaU~BDRq;J8f^`RdrLW%!flaj6EQYNR*%*dlBY^ltm;?&La{DN>ENU67&58HeS~I}=yD0W8Gc#5bqEDfTdqlk@~eZi8M8E4j`Rv!86pAb%aut)Ta%^qv9qP9WY1VFf#(C~Zd2KoiXF|1=};X?=0kD0&Bq77!rr$i=_sMUtIMW>G`vU@TS`{$>!r3~87GS}R>hDje7J0pr50vM`rdNL5J^jdviLS*L^%wufh=TXGbH+A1q^O#dxA#?Ur>Hbz&Otg*+`+3??Ta^+2Rd4_-HR6$WBcpepc=p=O7XNm0a;P1;O_1qV+7Yr;F%A4_>BO^r3qR!t^~9TNzZ>r*M5SYZTk;mRM(5_Dq@#s&^bA84QDIVZDgDQ9N%lq=it|-%t&I<%SP}1F0@#OtKjEavU4D4?a_gF{ikvt8A5BHAxY=<h)H9^#go=!r~^ZxhLTus|42?Y1VHl9C;?uo~PxfM9{VrU&2G;C2_1|{9F>TL<iwx&(yTsLYRc$lz7@5=Yl233G8G!yT`zI*1rCenu^IJ<luu&yIyi0qw_Zx`i5j1WaC17T-3)bz}^HPt)?IoO0J|kAkPT9QTFnN@Hn0xA+O<fMAb_Xw~G@(d7TgnGUZDRHA{!H*Q&VtYUPze$&X`bjgpl)J2Y%E-%88fG%9oQy(no?pnjh^D;9-s&?*xOU8V|kWZLRRP@hg!MA`b6$%LEl^$86+Ki*bgOL5*BOgD}4NOi`S+OvLwYcL`ps-~*iYNB+Qv~t#JI6cct$V<ml6t1}wt4cVIhuW-SKuwDG6~K@q8mFV*lVvM_bR9`1c~E|Sn{me=`B{mCm=@NQjpHP`o1`41vPsQ>v-*Z$5q-7xSD|Dgf(yM2ZMK^g_DcZnmKj*Q;wRV=IR2EGgm7<E!^flwTfQ}T@{qqX#9dDJ1ur0N?F$(iLB|EdXH+dJR<6xS2;1v)FmrRGts&*x1}?OsBu|Jmb{ad{D$eO&=HW-3^&m5WZAeO42&b{GqPZ6nQYBDLFO(T9A+E#7Bx6a@lDc3aC{{{z);TNQIRF;cZdpCuIRxOAMZOEC%HTb3@gfn8Fit9jRLOjKpg3jDS{ij_AYPHVYGWV=^rQqK0`$gcdyyo@!fd_r5KaIr$)yRj9Lb0+7b8@DJ}W^l<;+&fXH!1;D7%zK`pv<yh2|OF=y~l&_ZzbX{0G3yE)FHV`9wNW)aqBO7}dCY43FZ<I@Hh`Q;c{{mr~54+?iUTWfD@=Gl@`-9!ICDh0FzcrQ6Fu7!np@o64FbDJv_i?R|DgK~EtgvP}#Do|p*(f}U(x0pE-Y9jMi}6m@6fFkwR-VLfQ8D9#aKdQ1j+h9{}iO(qsiI<D=X{PfBlOTDCw;1Uuqxw`7G??VI>W%Q7E<6Ts@nG94Wzbw}>t*YI;6iKTb0zsS8W2O-B2;OAUO=&6E({c`0`3-6E&`t-^d5NHNsa#FqpQVVlQ@2AGHEP^pjGRf5%gMozfp-kTzVf$MztaMmsQK0bGUAmQ9Nz8dW}Pzv(mYPnW`fc<0Q9!9NL7jVFS$1xTe~q&5$DDzIXJYu^G@1dgx9Pk2pKhx+Zs!gNnNTp%PNnPLBAd2ELchCtB+{mc_?Qws&@5l5<4AnG&{A^))<@kaM+G)#Mlyff>lEy&^^iDU^X2u2w^1XJXOGM>Lg_9@6s9u4F5o2OM{LUIc24Yw-ES+77=9@l*ZhWQDcWNp+M$oZen`76Z8Qk>eB=#CC$ZBauJ!_M?2zSvhQxykT!I}Bfrm(<s}|A8*^xI%4|DTqup>~Yn#b~KwTpr?-|v7D{d)edq55mRbQHbp%+DZi>@}iKDb+mgL=6(a}GKV?*vzI#Xl2ve6<utkYuHAjD)`icSgGN2@{cXUIeeaTKmIu^Pvf*5K@iOGRsMLT?t=Ckuv097A6fWUO)eSuO{C^BA!zPK*-LYad+BwG(&Y5$r-2IJ69-~4Lz%#)6ki)tiWG$GcfXsD^9u_G#pSMfF^CwEuk$UY`Z#|Y~!0s$RtUM7Ziw&Y`McTkxWdnU{KY#)yuGxQo;H+7Z_J_VW<*TwW!d^{-~1RugH@1$E-3=7%3CU(J24~@hSm%3PPTCNo?m=B?K$UCSQrSH}tDX6-X8dPoRf3bf@%UBaU^3WWttq_$4PBoEzK{Hy*IpwG@!OQSb-y#99y4<B2YHof=lP(yW>!BunmGm3fR2aU_zKBkZxB>S`#wtdk|?Ez?9Q3p{sH^c*<i3}=3>54}-8B&<9lWr^-{Usw@`@8pgkEt(0tGT+2Skd>^xxiR$R=FeTpE0j=kRlzI*wvBTLXvB(h)hqNaUHLqSE|T;#(?WQeSUd^evEUFpKV;Cb#f~CthZL+fg-%JLpf>8&Ym=O71aFP$an-%DPeo`wm!4-jHmabG5=va8kJN=_S<Ni-TXJ+rPC2c{-N#z*K|0o|pyNHKrf>)RBv<hlaf<Sg9@4j`vmonn)dj^23KRP($xW0PP<sj)od*~)%SCdmCOE4cW>hCYXlubhQum`0y(qc8kPAnW3^jVprlPA)=s&st6g<gJVPcl1OG3gJ5ps%TmS#=dl`|yDaFs;B(i#s)6KU*IkoSr_9fH(of{LmC$x`=Z63D1Gm<gVH)D?SRzbgvL7UJC8Pjl-LLi;|wN`zXNriB!4I9Jw$`|m7?B~LCOr!BZlE5lDJrv}k(X4_Xh+=fx-gcwo*mZTzAF98p8xH$O5ON8S-n8N5Uv#D*PbkeHPLR~Jo&RUWnM)13B%!yZ%j``?Qh{%}9GB?513}8S}k)I*!Vx1<aQ^J=6eQVHBqZLb3`~3@<o9a@#^?Yb#Lf5Vc`#x3-Y%3-f$4r9goF)BNkU`3i*L~q|VF~n6CF{sosa92j3k(ZR2-qCoxD3nDf_0Y%GqEld#&1Zyvjtrx64J9HN>$R40}T;ZpA(b5dU^3sRm&Z2Y_lBcOfQ?iQmA&4?qjqOo=&29iqfe8uk0vVnr00hDm7WVApV$yK|Gogu5d$g`*hZA{St@P{^`X^q@M1}P9p78`V{R6L4}E60d_lo`uzUp?XPccADN>xj}okH<b7j&DT^+5O#VP4i*kp!eagu~+EPw2BT#hD6GWqfZPq0uNFLClVxlL3;`6S79F-TgWL}_TW#e&eA&cUgR=LgV)SU!HA1B5r@fO?G1>Y>`n$O7$UV&|d9MWo`OdW+dzBJ*X^*qiq@8M=cj;>zgtWZRca9xdnmB-y-%#;>Ru}2*OTX1f5GRi<I3L&lkEw45=YLs?N#V#u~Rb)HZb`FV=$ONniqDGM*kzwDFN@Yo4GHpRoaNYIxgoHsox8B;%x=3=4;7rpt^MWzlzR++VE$tJ!t@34u^v*RMc|$cyl3wZ|=|HpJU;c48Mx;iC^|MOQZUj@|UNz;7<?Uw)WIIu%rk*rbJ&{Nw<<z!Nv&ubMjkdEN*7NenrAy1N>lt8e?WBjGkOU^AjIq0lgxcd1kK`}$B3}Z}O3JzElSs&Q;Hh3UQMG77=IE+a3Py33g4<de2p2|>09r&ltcxXXRsa+bgj9B>wgmLzZB*$dIArobHp$I8xoo27K~=*;DnL~T%hRRIz!ZobS~cs{@n<r949KHAR?-!gUaut!92X(J{fMc+#06a<qZ*?|9?mN_KM5A*f<J_HyY!2bMjF@HWm}hOEL)r>UHn}9N(SBctbKz{(Y+(EhGv&6Y?RsJ%%-DwnTIZL{pC|X2A~SYW7)zlRhXId8I|EX4a9}pTjr&(oZ@6Mg}MeYlQlm&X^a@n7iu3;#Lk!Elq?YvmJa_9PyVP`'
)).decode("utf-8"))

_SELLABLE = ("STRAWBERRY", "MELON", "MILK", "WOOL", "EGG", "TOMATO", "CARROT", "WHEAT", "FERTILIZER")

_FRONT_RUN_HORIZON = 1
_FRONT_RUN_ITEMS = ("MELON", "STRAWBERRY", "MILK", "WOOL")
_BASE_PRICE = {"MELON": 250, "STRAWBERRY": 120, "MILK": 160, "WOOL": 200}
_GLUT_WEIGHT = {"MELON": 3.5, "STRAWBERRY": 2.0, "MILK": 2.0, "WOOL": 3.2}
_LAST_STEP = -1
_CLONE_CONFIDENCE = 0


def _public_signature(farm):
    """Compact public fingerprint for detecting a mirrored build."""
    counts = {item: 0 for item in (
        "COW", "SHEEP", "GOOSE", "WHEAT", "CARROT", "TOMATO",
        "STRAWBERRY", "MELON", "PASTURE", "COOP", "WEED",
    )}
    for row in farm.get("tiles", []) or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            for key in ("animal", "crop", "kind"):
                value = tile.get(key)
                if value in counts:
                    counts[value] += 1
                    break
    positions = [farm.get("farmer", [0, 0]), *(farm.get("hands", []) or [])]
    return (
        len(farm.get("hands", []) or []),
        tuple(sorted(farm.get("unlocked_quadrants", []) or [])),
        tuple(sorted(tuple(position) for position in positions)),
        tuple(counts[item] for item in sorted(counts)),
    )


def _signature_distance(left, right):
    distance = abs(left[0] - right[0])
    distance += 3 * abs(len(left[1]) - len(right[1]))
    distance += sum(abs(a - b) for a, b in zip(left[3], right[3]))
    if left[2] != right[2]:
        distance += 2
    return distance


def _update_clone_profile(obs, step):
    global _CLONE_CONFIDENCE
    if step not in (4, 24) and not (step >= 48 and step % 24 == 0):
        return
    farms = obs.get("farms", []) or []
    if len(farms) < 2:
        return
    player = int(obs.get("player", 0) or 0)
    distance = _signature_distance(
        _public_signature(farms[player]),
        _public_signature(farms[1 - player]),
    )
    if distance <= 1:
        _CLONE_CONFIDENCE = min(8, _CLONE_CONFIDENCE + 1)
    elif distance <= 4:
        _CLONE_CONFIDENCE = max(0, _CLONE_CONFIDENCE - 1)
    else:
        _CLONE_CONFIDENCE = max(0, _CLONE_CONFIDENCE - 3)


def _front_run(action, obs, step):
    """Sell one premium line immediately before a clone's expected glut."""
    if _CLONE_CONFIDENCE < 2 or _FRONT_RUN_HORIZON <= 0:
        return
    orders = list(action.get("market", []) or [])
    if len(orders) >= 10:
        return
    already = {}
    for order in orders:
        if isinstance(order, list) and len(order) >= 3 and order[0] == "SELL":
            already[order[1]] = already.get(order[1], 0) + max(0, int(order[2] or 0))
    planned = {}
    end = min(len(_TRACE), step + _FRONT_RUN_HORIZON + 1)
    for future_step in range(step + 1, end):
        distance = future_step - step
        for order in _TRACE[future_step].get("market", []) or []:
            if not (
                isinstance(order, list) and len(order) >= 3
                and order[0] == "SELL" and order[1] in _FRONT_RUN_ITEMS
            ):
                continue
            item = order[1]
            quantity = max(0, int(order[2] or 0))
            if item not in planned:
                planned[item] = [distance, quantity]
            else:
                planned[item][1] += quantity
    shed = (obs.get("private") or {}).get("shed") or {}
    prices = ((obs.get("market") or {}).get("prices") or {})
    choices = []
    for item, (distance, quantity) in planned.items():
        available = max(0, int(shed.get(item, 0) or 0) - already.get(item, 0))
        quantity = min(available, quantity)
        if quantity <= 0:
            continue
        price = float(prices.get(item, _BASE_PRICE[item]) or 0)
        priority = (
            price * quantity * _GLUT_WEIGHT[item]
            + (_FRONT_RUN_HORIZON + 1 - distance) * _BASE_PRICE[item]
        )
        choices.append((priority, item, quantity))
    if choices:
        _, item, quantity = max(choices)
        orders.append(["SELL", item, quantity])
        action["market"] = orders[:10]


def _terminal_liquidation(action, obs, step):
    """Replay-derived safety net: leave no sellable shed inventory at season end."""
    if step < 680:
        return
    shed = (obs.get("private") or {}).get("shed") or {}
    market = action.setdefault("market", [])
    already = {
        order[1]
        for order in market
        if isinstance(order, list) and len(order) >= 2 and order[0] == "SELL"
    }
    for item in _SELLABLE:
        qty = int(shed.get(item, 0) or 0)
        if qty > 0 and item not in already and len(market) < 10:
            market.append(["SELL", item, qty])


def _shed_access(size):
    half = size // 2
    return [(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)]


def _move_toward(pos, target, tiles):
    x, y = pos
    tx, ty = target
    choices = []
    if tx < x:
        choices.append(("WEST", (x - 1, y)))
    if tx > x:
        choices.append(("EAST", (x + 1, y)))
    if ty < y:
        choices.append(("NORTH", (x, y - 1)))
    if ty > y:
        choices.append(("SOUTH", (x, y + 1)))
    size = len(tiles)
    for op, (nx, ny) in choices:
        if 0 <= nx < size and 0 <= ny < size and tiles[ny][nx] != "LOCKED":
            return [op]
    return ["PASS"]


def _terminal_action(obs):
    """Observation-driven final-eight-turn harvest/drop/sell controller."""
    player = int(obs.get("player", 0) or 0)
    farm = (obs.get("farms") or [])[player]
    private = obs.get("private") or {}
    tiles = farm.get("tiles") or []
    size = len(tiles)
    positions = [farm.get("farmer", [0, 0]), *(farm.get("hands") or [])]
    inventories = list(private.get("inventories") or [])
    inventories.extend({} for _ in range(len(positions) - len(inventories)))
    sheds = set(_shed_access(size))

    available = {
        (x, y)
        for y, row in enumerate(tiles)
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
    }
    actions = []
    pending = {}
    for pos_raw, inventory in zip(positions, inventories):
        pos = tuple(pos_raw)
        inventory = inventory or {}
        load = sum(max(0, int(v or 0)) for v in inventory.values())
        x, y = pos
        tile = tiles[y][x] if 0 <= y < size and 0 <= x < size else None
        if load > 0 and pos in sheds:
            action = ["DROP"]
            for item, count in inventory.items():
                if item in _SELLABLE:
                    pending[item] = pending.get(item, 0) + max(0, int(count or 0))
        elif isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0:
            action = ["HARVEST"]
            available.discard(pos)
        elif load > 0:
            target = min(sheds, key=lambda q: abs(q[0] - x) + abs(q[1] - y))
            action = _move_toward(pos, target, tiles)
        elif available:
            target = min(available, key=lambda q: (abs(q[0] - x) + abs(q[1] - y), q[1], q[0]))
            available.discard(target)
            action = _move_toward(pos, target, tiles)
        elif isinstance(tile, dict) and tile.get("fertilizer_available", False):
            action = ["COLLECT_FERTILIZER"]
        else:
            action = ["PASS"]
        actions.append(action)

    shed = dict(private.get("shed") or {})
    for item, count in pending.items():
        shed[item] = int(shed.get(item, 0) or 0) + count
    prices = ((obs.get("market") or {}).get("prices") or {})
    sells = [
        (int(shed.get(item, 0) or 0) * int(prices.get(item, 1) or 1), item, int(shed.get(item, 0) or 0))
        for item in _SELLABLE
    ]
    sells = [row for row in sells if row[2] > 0]
    sells.sort(reverse=True)
    market = [["SELL", item, qty] for _, item, qty in sells[:10]]
    if int(obs.get("hour", 0) or 0) <= 1:
        already = int(farm.get("hires_today", 0) or 0)
        for _ in range(min(10 - len(market), max(0, 8 - already))):
            market.append(["HIRE"])
    return {"farmer": actions[0], "hands": actions[1:], "market": market[:10]}


def _base_agent(obs, config=None):
    global _LAST_STEP, _CLONE_CONFIDENCE
    step = min(int(obs.get("step", 0) or 0), len(_TRACE) - 1)
    if step == 0 or step <= _LAST_STEP:
        _CLONE_CONFIDENCE = 0
    _LAST_STEP = step
    _update_clone_profile(obs, step)
    if step >= 714:
        return _terminal_action(obs)
    action = copy.deepcopy(_TRACE[step])
    _front_run(action, obs, step)
    _terminal_liquidation(action, obs, step)
    return action


# ===========================================================================
# Market-controller overlay
# ===========================================================================
import math as _math

# Per-step remaining sell volume of this field plan, measured over c27 self-play.
_SUPPLY = json.loads(zlib.decompress(base64.b85decode(
    'c%1Fr%Wm5+5Cza*39{~j!?(Ii3pWj#)PQRsXp4SH(SNTlZOK$D%hrRG91k$}ECK|GWl5pP5&z!5eqB9m??2xC_S${8>%g|40o8~KRn)i|T_c-Ng)B~CGN496wl}hgs1QXm@KJ@zO8JSLEoMTcp!~L+F{jWC^e|LF)=(2sf$PIb3(SlNzsDBEF#JfoWe(t$Yj9w9c;Cbw<7UNFSXW_+8eK!jXnZ0v6}ZhU25LvUVmLTB{V)npQt&Tu2T?{8u6>1DeP;Bfh-txjrG(rgadmg#C&QQ5mb7*zObT%PjIEHq#)0xwmcrH0IS6;r%ds_7fjeO<R-XVDHtFe5b{U9c@TIh4Qa~f2^712`IfKEUA#@B*lD={N5Gf8RziqLrKOgSyKR;|X>+lpP>YsCQadB~Rad9Oo3_rH(mxt||haX&ATwGjSTv-akk00C3!|SKjX7dw65Q*tshG7_nVVGkyprl}RZvx~bgg>YpF-fdKOSG4qgU%8bqxwVs6t+gzh!`qtez1P$MN(W?6824OUyMG5Y$A?9(^>?+g>mRks6oAK>ZeGxbZYtsodn6F-$d?$<E};~EL)F^?O7_S=&9^w^}PO$2eRE-I>Ru`&4T`{s6B{cFwQ{YZl6U*zQ14uWyS3#%h2Z*@^*MPQP3v8n8;y4cWAPRbdmZHJgFv)oG)UwHJsJsBlnMRadB~RadBm-FjM*T{4I2j>|PvW80OtT4e<Ic^F9%mLxt<aObni{eUSnSOm>`25B5IDhw)1T#~HJ2gbkb)it^`?XCZfm;OhyiIuT((rx*gdOtM5Af}2MpCW=~4u!#b8dq^Fe(W!z<VQjEXR6G?ub;2p#H~XpMB5DU|K3=`9*UzC3<m5IO40GEoV6^e>(Kih?vsxDB>cI}F?O-s7>4zgO*m=mOMPEO7fFHFt)1`zxoKzFEYZV<Sf2W`*g3~vl6)Si2btbe1*(mA?61N3mCrB|}<jgtQPJ>6GFRRV=>G|o`Y7^F*FlVr6C;{`%5t~lbSY!)lcb=RE!hfF_mzI-r-D(o354i67ZQuEZwrOsCA(S1oU{8hVL>-fNRvtUO?m%zt9OxwICh{0%a-kZ?nHV;0J{oL}oHQfG!C2wLe($Yu`<RKME{uGWj?HT?+Td1C5YbH5F*r?^*4GKtKIO3v+vWF6XxHyrn;6*2-<p>3c(Rs!pD~m+;RUgj8S*-S*aeT2QB@B!|NaA0p<>w'
)).decode("utf-8"))

_I0 = 10000
_PRICE_FLOOR = 1
_MP = {
    "WHEAT": (25, 400, "sqrt", 0.80, "log", 0.20),
    "CARROT": (35, 450, "log", 0.20, "sqrt", 0.70),
    "TOMATO": (60, 200, "linear", 0.40, "sqrt", 0.60),
    "STRAWBERRY": (120, 100, "sqrt", 0.70, "linear", 1.60),
    "MELON": (250, 300, "log", 0.20, "sq", 3.60),
    "EGG": (50, 332, "linear", 0.40, "log", 0.20),
    "MILK": (160, 122, "sqrt", 0.60, "linear", 1.60),
    "WOOL": (200, 105, "log", 0.20, "sq", 3.20),
    "FERTILIZER": (100, 200, "linear", 0.40, "linear", 0.40),
}
_SHOP_DEMAND = {
    "BAKERY": ("EGG", "WHEAT"),
    "PIZZA_SHOP": ("MILK", "TOMATO", "WHEAT"),
    "BRUNCH_SPOT": ("EGG", "WHEAT", "STRAWBERRY"),
    "YARN_STORE": ("WOOL",),
    "ICE_CREAM_SHOP": ("STRAWBERRY", "MILK", "WHEAT"),
    "PET_CAFE": ("CARROT",),
    "SMOOTHIE_SHOP": ("STRAWBERRY", "MILK"),
    "FARMERS_MARKET": ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY"),
}
_CENTER_ITEMS = tuple(k for k in _MP if k != "FERTILIZER")

# Products the controller owns, mapped to a reservation price expressed as a
# fraction of base price. Everything else keeps the tape's schedule untouched.
_RESERVE = {}
# Sort SELL orders by gross value so the most valuable sale takes the earliest
# slot; market slots resolve index by index across both players.
_SORT_SELLS = True
# Ranking key for slot placement: "gross", "unit" or "impact".
_SORT_KEY = 'impact'
# True places promoted sells ahead of buys/hires; False keeps the tape's layout.
_SELLS_FIRST = False
# Only these products may be promoted into early slots. Empty means all.
_PROMOTE = ('MILK', 'WOOL', 'STRAWBERRY', 'MELON', 'EGG', 'TOMATO', 'CARROT', 'FERTILIZER')
# Extra slot priority for a product whose remaining supply outruns the town's
# remaining appetite. Such a product is a race, not a hold: its price will only
# fall, so the units sold before the opponent's are the only ones worth much.
# Ranking purely by current price gets this backwards — a already-crashed product
# looks unimportant precisely when beating the opponent to the floor matters most.
_RACE_WEIGHT = 0.0
# Products that may be promoted only from this step onward. Selling wheat early
# lowers the price an opponent pays for feed, which can rescue a cash-starved
# rival; deferring wheat promotion keeps that pressure on during the early game
# when starvation actually bites.
_PROMOTE_AFTER = {}
# Products promoted only while the opponent's public money is at least this much.
# A rival near insolvency is the one most helped by our extra supply, so we hold
# that pressure on until they are clearly solvent.
_PROMOTE_IF_OPP_MONEY = {'WHEAT': 200.0}
# Force selling once the shed reaches this load, protecting end-of-day drops.
_SHED_PRESSURE = 80
# Reservation decays linearly to zero across this window, spreading liquidation.
_RAMP_START = 576
_RAMP_END = 716

_SUPPLY_DRIVER = {
    "MILK": ("animal", "COW"),
    "WOOL": ("animal", "SHEEP"),
    "EGG": ("animal", "GOOSE"),
    "FERTILIZER": ("animal", None),
    "STRAWBERRY": ("crop", "STRAWBERRY"),
    "MELON": ("crop", "MELON"),
    "WHEAT": ("crop", "WHEAT"),
    "CARROT": ("crop", "CARROT"),
    "TOMATO": ("crop", "TOMATO"),
}


def _mshape(func, x):
    if func == "linear":
        return x
    if func == "sq":
        return x * x
    if func == "sqrt":
        return _math.sqrt(x)
    if func == "log10":
        return _math.log10(1.0 + x)
    return _math.log(1.0 + x)


def _mprice(item, inventory):
    """Exact port of the engine's market_price."""
    base, throughput, below_f, below_t, above_f, above_t = _MP[item]
    if inventory < _I0:
        amp = below_t * base / _mshape(below_f, throughput)
        value = base + amp * _mshape(below_f, _I0 - inventory)
    else:
        amp = above_t * base / _mshape(above_f, throughput)
        value = base - amp * _mshape(above_f, inventory - _I0)
    return max(_PRICE_FLOOR, int(round(value)))


def _remaining_drain(item, step, shops):
    """Units of `item` the town consumes between `step` and the season end.

    Shops fire on steps divisible by 4, the town center on steps divisible by 12
    with multipliers that step up on days 10 and 20. Still-locked shops are
    credited from the day they are expected to unlock (one new shop every three
    days), so late-game demand is not understated.
    """
    if item == "FERTILIZER":
        return 0.0  # neither the shops nor the town center consume fertilizer
    unlocked = set(shops or ())
    live = 0
    pending = []
    for name, products in _SHOP_DEMAND.items():
        if item not in products:
            continue
        weight = 2 if len(products) == 1 else 1
        if name in unlocked:
            live += weight
        else:
            pending.append(weight)
    n_locked = len(_SHOP_DEMAND) - len(unlocked)
    pending_total = sum(pending)
    is_center = item in _CENTER_ITEMS
    total = 0.0
    for s in range(step, 720):
        day = s // 24
        if s % 4 == 0:
            total += live
            if pending_total and n_locked > 0:
                expected = min(n_locked, max(0, day // 3 + 1 - len(unlocked)))
                total += pending_total * (expected / n_locked)
        if is_center and s % 12 == 0:
            total += 4 if day >= 20 else (2 if day >= 10 else 1)
    return total


def _count_driver(farm, kind, name):
    total = 0
    for row in farm.get("tiles") or []:
        for tile in row or []:
            if not isinstance(tile, dict):
                continue
            if kind == "animal":
                animal = tile.get("animal")
                if animal and (name is None or animal == name):
                    total += 1
            elif tile.get("kind") == "PLANT" and tile.get("crop") == name:
                total += 1
    return total


def _opponent_scale(obs, item):
    """Opponent's expected remaining supply of `item`, relative to ours."""
    driver = _SUPPLY_DRIVER.get(item)
    if driver is None:
        return 1.0
    farms = obs.get("farms") or []
    if len(farms) < 2:
        return 1.0
    me = int(obs.get("player", 0) or 0)
    kind, name = driver
    mine = _count_driver(farms[me], kind, name)
    theirs = _count_driver(farms[1 - me], kind, name)
    if mine <= 0:
        return 1.0 if theirs > 0 else 0.0
    return max(0.0, min(2.0, theirs / float(mine)))


def _reserve_price(item, step, obs, shops):
    """Reservation price for one unit of `item`.

    A fixed fraction of base price, decayed linearly to zero over the
    liquidation ramp, and scaled down when the town's remaining appetite cannot
    absorb the supply still to come: a structurally oversupplied product is a
    race to sell, not something to hold.
    """
    base = _MP[item][0]
    frac = _RESERVE[item]
    if step >= _RAMP_START:
        span = float(max(1, _RAMP_END - _RAMP_START))
        frac *= max(0.0, (_RAMP_END - step) / span)
    drain = _remaining_drain(item, step, shops)
    supply = float(_SUPPLY.get(item, [0] * 721)[min(step, 720)])
    ahead = supply * (1.0 + _opponent_scale(obs, item))
    if ahead > 0.0:
        frac *= min(1.0, drain / ahead)
    return base * frac


def _plan_sells(obs, step, slots, short_of_cash):
    """Choose SELL orders for the controlled products."""
    if slots <= 0:
        return []
    shed = (obs.get("private") or {}).get("shed") or {}
    inventory = ((obs.get("market") or {}).get("inventory") or {})
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    load = sum(max(0, int(v or 0)) for v in shed.values())
    forced = load >= _SHED_PRESSURE or short_of_cash > 0

    candidates = []
    for item in _RESERVE:
        held = int(shed.get(item, 0) or 0)
        if held <= 0:
            continue
        inv = int(inventory.get(item, _I0) or _I0)
        if forced:
            units = held
        else:
            reserve = _reserve_price(item, step, obs, shops)
            units = 0
            while units < held and _mprice(item, inv + units) >= reserve:
                units += 1
        if units > 0:
            candidates.append((_mprice(item, inv) * units, item, units))
    candidates.sort(reverse=True)
    return [["SELL", item, units] for _, item, units in candidates[:slots]]


def _cash_needed(orders, obs):
    """Coins this turn's buy orders require."""
    seeds = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
    animals = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
    prices = ((obs.get("market") or {}).get("prices") or {})
    total = 0
    for order in orders:
        if not isinstance(order, list) or not order:
            continue
        op = order[0]
        if op == "BUY_SEED" and len(order) >= 3:
            total += seeds.get(order[1], 0) * int(order[2] or 0)
        elif op == "BUY_ANIMAL" and len(order) >= 3:
            total += animals.get(order[1], 0) * int(order[2] or 0)
        elif op == "BUY_PRODUCT" and len(order) >= 3:
            total += int(prices.get(order[1], 50) or 50) * int(order[2] or 0)
        elif op == "BUY_LAND":
            total += 4000
    return total


def _race_factor(item, step, obs):
    """1.0 when the town can absorb everything still coming, higher when not."""
    if _RACE_WEIGHT <= 0.0:
        return 1.0
    shops = (obs.get("town") or {}).get("unlocked_shops") or []
    drain = _remaining_drain(item, step, shops)
    supply = float(_SUPPLY.get(item, [0] * 721)[min(step, 720)])
    ahead = supply * (1.0 + _opponent_scale(obs, item))
    if ahead <= 0.0:
        return 1.0
    glut = max(0.0, 1.0 - drain / ahead)
    return 1.0 + _RACE_WEIGHT * glut


def _sell_priority(order, obs, step=0):
    """Rank a SELL order for slot placement; higher goes into an earlier slot.

    Market slots resolve index by index across both players, so an order in an
    earlier slot is priced before the opponent's matching order in a later slot.
    ``gross`` ranks by revenue at stake. ``impact`` ranks by how much revenue is
    actually lost by going second, which is the quantity times this order's own
    price impact — that promotes steep premium curves (wool, melon, milk) over
    large but nearly flat staple sales (wheat, egg).
    """
    if not (isinstance(order, list) and len(order) >= 3 and order[0] == "SELL"):
        return -1.0
    item = order[1]
    try:
        qty = int(order[2] or 0)
    except (TypeError, ValueError):
        return -1.0
    if qty <= 0 or item not in _MP:
        return -1.0
    inventory = ((obs.get("market") or {}).get("inventory") or {})
    inv = int(inventory.get(item, _I0) or _I0)
    unit = _mprice(item, inv)
    held = int(((obs.get("private") or {}).get("shed") or {}).get(item, 0) or 0)
    qty = min(qty, held) if held > 0 else qty
    race = _race_factor(item, step, obs)
    if _SORT_KEY == "unit":
        return float(unit) * race
    if _SORT_KEY == "impact":
        return float(qty) * float(unit - _mprice(item, inv + qty)) * race
    return float(unit) * float(qty) * race


def agent(obs, config=None):
    """c27 with its SELL layer partially replaced by the market controller."""
    action = _base_agent(obs, config)
    try:
        step = int(obs.get("step", 0) or 0)
        if step >= 717:
            return action  # proven terminal controller; leave untouched
        orders = list(action.get("market") or [])
        keep = [
            order for order in orders
            if not (
                isinstance(order, list) and len(order) >= 2
                and order[0] == "SELL" and order[1] in _RESERVE
            )
        ]
        player = int(obs.get("player", 0) or 0)
        money = float(((obs.get("farms") or [{}])[player]).get("money", 0) or 0)
        short = max(0.0, _cash_needed(keep, obs) - money)
        sells = _plan_sells(obs, step, 10 - len(keep), short)
        if not _SORT_SELLS:
            action["market"] = (sells + keep)[:10]
            return action

        def is_sell(o):
            return isinstance(o, list) and o and o[0] == "SELL"

        opp_money = None
        if _PROMOTE_IF_OPP_MONEY:
            farms = obs.get("farms") or []
            if len(farms) > 1:
                opp_money = float(farms[1 - player].get("money", 0) or 0)

        def promotable(o):
            if not is_sell(o):
                return False
            item = o[1]
            if item in _PROMOTE_IF_OPP_MONEY:
                if opp_money is None:
                    return False
                return opp_money >= _PROMOTE_IF_OPP_MONEY[item]
            if item in _PROMOTE_AFTER:
                return step >= _PROMOTE_AFTER[item]
            return not _PROMOTE or item in _PROMOTE

        # Only promotable sells compete for the earliest slots. WHEAT and
        # FERTILIZER are the only products an opponent can BUY_PRODUCT, so
        # promoting those ahead of their buys would lower the price they pay for
        # feed; those sells are deliberately left in their tape position, where
        # the opponent's buys have already drained inventory and lifted the price.
        merged = [o for o in sells if promotable(o)] + [o for o in keep if promotable(o)]
        merged.sort(key=lambda o: -_sell_priority(o, obs, step))
        rest = [o for o in sells if not promotable(o)] + [o for o in keep if not promotable(o)]
        if _SELLS_FIRST:
            action["market"] = (merged + rest)[:10]
        else:
            # Keep the tape's slot layout: sorted sells refill the slots that
            # already held promotable sells; every other order stays put.
            out = []
            queue = list(merged)
            for order in keep:
                out.append(queue.pop(0) if (promotable(order) and queue) else order)
            out.extend(queue)
            action["market"] = out[:10]
        return action
    except Exception:
        return action
