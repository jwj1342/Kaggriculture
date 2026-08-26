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
    'c-rk<U2j`glKd-ypXb5+5GC)MVsj?OD3Kw{L(B$55MXApz+(0xyKjsA?`w}F^4`npuBtxgQgYT$VQ7jxAAQd4uCA{B`F~#h+poX<<L|${`j_v1e)avQ_c!l;`EdR5{?py|)&39Pz54fG|MPGE_2u8b{Lepr{p~;g{@-8z@8?%PynpzF{_6WrfBoh9r}sZz-@N+#U2ku9pZ~K2|MKyN?e@dy-#%`)@4o!Y?uYI5{pS~#C;#%}_U87d&o36oKl*TY`|i`*`{Cbh_WS?+!*`<@e|Z1)&!0XFe|9mN_Rp_&+mH7T6Zq-&?*4~|m&Z4!ucqttaeH$!9K-5#42SO>{wyBYXb^*!CmV-{bMn*4h6gi0j_Y9u7n4<Z{3!X|4>#9ux7n)WX&(Lz|Mp}yWDHM#H(GTxu7AG$)4-A@3-PqI@n@yI*j}HGXJB2|_uIQuJ3M)JYJb5|Se}~U$J<Y*W{3>^k6#Ym<h|*v+5W@Do9x8NG7cvG_WH@r4<CHE1BS~|Fo3~=q7fX{X!J>Gd*La^TZzxu>5(A6__R-OS%<3y_85K6+~cP$V#_=J1#rFx3yt<QwDE;_)xtxTT>JcPn@mjK0DSFf+kF_kx8UA;+SbEme!Ab#jw<_XF7)x|j;}sH8b0Dzm9-u0P=}v*`ZzO|nSP2HO4n%}zGC>R^ZbJH>e+wb<Y~A{d~e~Nw;z1Hf8q4*_iv16AJeHrM*aYJP`$_W_V(sx`}Y2qKW^{t-`~9d*Xga)eVH47&^EQk-#f#e9h{WG5c3mzi~>*oBy?Ub_O{df6&^9$JWkhO-3(Jmj&mO$4f@2u{T@a-;6T)aJm{I>GZ)SD@x&B@4>GIq67YFTs|!IJ*QF<sV(?P=X0lB9rS#1t{4yNxW)LBpMO!$Vt-KycsHc*lEt=ir(PkIuLWL)#?+q{yH(G-s)Zn|3_pDtt2sq2Va&5%^_e$P=in%^xxbp35pYLl;uLio4YbzVm>iT5<5PEz}Ge3)y9M0!k`0h5q?c^IebszMLyXqz#e}8yuRviI(HtiGk7dS`+^>}<Sf1!tG#XN`lvQhUfL%IEERhX6QIx<fyca6&4DLY3409nG}bCi=Wl?FoFPlOZ9^Y@Q$e*1xMKk)4bOl-5Go0oE8B9_fYK_D+`Fj>r(K_dYUA&IP2AgwKw_i(c=`FrjX)={nkIBCx*C%JTj8i@ZAt=tdScYleeJA*^xqCN(N1h3>_hHVQtTBr_eAhdQUeSakV^uWvL?i?rlFoeqPVAt}vW}~Il;4TQHjcs>e>xU&9@CLly8GJQ<GLC+G80VOH+bQ9SJ&ECu)d?NwCjhhZn`89t2VMY2<U;ZtpFVx{aKj*v@*<>XFKiF<$#wg9e|Nq6etUQKSDYuR<BZxwld*){@ws3}Hezc?-H^%Wz#|KOfahbMf|8AnK?V{v0+92&nj?p73^`VCMhc$wu&m>&qr;+oua3nY9F4)v5OVtGpa%4a|4x>t&4A)HvH#&=+>PEce)%x+Iz0hBrgK8ASkGdAZyjAe0|EG3GWTo95pR6(@S=}Hw{kod^}g5g$jx3Gek7>K2!miaDp!9<=J?d;F~7ULy?KCeBj5As15X?I`7(d^D%{rP-UMx;b#UIVU-N{<)R}~Ky6VXT%!v=Cd(^xu267v4GcHBSA1X+l%@u0cPZHtjiQ!iB#14E1HmMaGcHv7RrhtT?%E^J#m#xV8Hm*&p3>pIQCsc;YpfNx_<WWwlx4NAycVUo~;7j=Af~p@avK#oNxn%IdL-~r6ipLgaD2(@}vA{We$W2MjVbPGbp5}wsnv)qxDAb%!gG8w#5l%XHN`EThU07=Zs~$u{g8l?~8oL0Lihb|}jNS(xO7u|<3prO5v5rVrLQ)^8xInTu!V0)kMyL!75!m#YI`xoYXfoG=ObDr?IVM<BSq??rpo5P@jwaJL@B~zdm_pHzqd)5tGfY=oVuHd|HJye$Fhe8?xNX^}+mPynToJATaop;j6LfI^gW**3rLZ+<VG<{f_;?k^kEL63=d#Pzpwp5scs>*&U4e23-3l5dUmX2&;qE1iPo_-%t}XOb5(VL_!UpB_a-`Jn3<Z0ZtVt7A52F!J^rY$cA!Vx^+#REWSPS9D_cwo*!^y#iJ2IIUuk)nEI*cb*dplB&K0$p>JGv~F?HzpzlJXFp=@J3hijj{lh#Sl?zt?)zSzUoe{^$%j#C5j<GS{g*48pWAcgI3-CMjF1{7#RA0CJ6?XQ4#n7DvA|t3X_Nd~EbW%q}Gj@S6cT6JXI>T~*F2AVrqI?$iKDvn!}e0WXXq2DU3LinNl^Q^bSsS9>!Gfl(ndi)gGkds4q7Vt#$<{fElEp)Y~H9<EW{Y36k}k~&Iw?;MX&InJ4Wg>;VOSbkbIQ5axac`>zuk!7mUe*CKK7KW>oTir|pB_Th%1j;x-CqzKlcs1<nu$XA9bl1-}JY12}x^7Ydej&n^p%)*7nM+HyVZ~;yWGN@1r<D|!BsJX_WfP(Pp>|L7?9M-I$VScz7(fq%$9g%7-%qid!I=;;qldB&akK<(!08PNEQyodi)Crf+d&ny2nBg^=)|P`Cj0@5JuOr**hjMFI<!tqed>d8khq8Pt0s)o_1?^pp;eGd?g@m&a<nARrc6w|2npUpc0l9A^g^jv>bey3XMVSM_pSFn$8k%d>Tm^x(;%5#A(lcn8r5bns0T7ZSe8@C8NG6jQ;r<P^HP7N!c<_uEJ5U1-1CJ@pCJv&N)-2vB^=-|AS4I_rEM0)5FIl-2eA|!t4M6?`D~bdo_=8yAlxax3;)=ajDuoD*O7k3xgx=49qIE8ylJIh;4r_I<;;l_FJ_pqfcoVPvnpWy!U3U1=tFZ2Ht`cMCw`n^v|X4TKGq>JJMv_RG`8xPYte7;RJz>P)7S9l-Pt-AR6T5j#?&xWfq=pY1`Udg$hB3e8Uo;ERq~oeEm3y5!s%}if6i^hQq~kTw$lYK7v)1Z1fI*$Z%4ZzQcl{mZ*&F=G=)GQAlJ<fvJ8vYd($*%4x89)CcS75{$g+57MYk%N+JOhCKgm)eFl{o{WZ~^WQEF!LPj)!E100O0a&b-iY=Z1F?fPb<}H}ihOm-N^frG;<$Dt==F>*e-i%H5A=yS+O7cjM9d~)xm2|b)O~0N`I=9_u++<s`9@CM1Ach5<n6lH0)V447W&SKDxv@PzZAs^d5O-M}6}aN@Ox!hInsvys<|de*7iDo`3HgQJAddO4#GQ~5ibb$J?WYd+Ep4DEICSb1%DvYSLzTZrObY##mVFehP~0!M^>k3qUZswC8IkqA8$&8MtfRV;T({$>0@kL~F_zq2m8n#l6miRn#y2ma+A1Y?TUg2&X;cFTM(5ttQ7(z0P>1Y@x&=fD>XmV5!*~VMaCPhQfR-{w!$;~oC8mYp$xo<JR2g11nC5P`KUoNYNpWGff}AN&(zg=<MgR$O(!_MIS#aA;uuO-D2qA=#GF*XBB5?^vOPDyswTAjr=d+}-NeDtZO?JdcOHHgDzs8jC5OtWkN?QiS^~nVDvKT?@hd|;4PJ&t6f<Y3x@(%Ps%Hu)d;1F)6UET*JL4mEo%vpx8c}Nz#)H=}<DT*flJN#tVJI)XyP2*`ild4tOk4hr_#gaM{?PM4zky35CsLY-bslB@|=eITZKqU`8bF6fhUDBqovI74IVti6-Jl8#jIjXg~N0#iG%hJ?(!w$+v;TMVxHLB3s5JO8)@bgp{=CIiD{m}rg1T5{WKpBM0c#{M2W*HwJs1G?Mg-wJu7^pY&Lb$3_7czbfA3S=+g+Zj47MV+(HrT6RvWL1Nu{Xi=h%yR6T(lIq+hW4V${8v%7H7dF(ZYMERtjvB7zuR^tM`y4R)Nie&622z;;3x*%a=FWO+A$i-*nqG<h*AZUnBU+Bvx8|Nv>S=CC*gU34VaLC7tc{zRXw61#FBP%BbRlb5L98Fy*dlHMmhd3dbMk;B8SlIfoXRP6q9WVj7|tGpR`@aivV}amK!BSZ)iKsbPCFafO;gcnuD$?m*7)u8mXNq3V!xbhRDS(v?<KGB-4g=FwHbpQcg6O9TQOu!Nb}3+5rIBd($)k8&GVF%1ch;0+{MUVYub%5zYV@*GuEYoiF+_EC3E^G^-b6i1k<o@SS+nnHaOr}LK^|3Pz@Hsk54BE@~v=>2+!Z`G>sn(MG)b8sa$k07}^%k39F+|WQ#P=rJFmeU$ELP`_f2IC4CZt3f1Q3bnoPBefGT3*+q@g;ij;2%zjT8c_}xgToY=g3%GQ{Sx2K_k_AlvzfKh)nd2+yr!Ap~sr(S9fcj${;ufSt{AnOz^8BfNO~f8-!I#A+7fmWA?}^W$}ojB1h>a!0N)O=5El$@9^&mIYikiA>rN#Ucup`DUX&oc$*c=h=!9JJ5fVMWl8G4%EdY=e1gainCOrW4E_n+xyC819sIUGvt!QPS@$asn@LuD)(N$7Ti(RLOjh^)5`Y<A2!?Y^GXO4w2NQIPQVgkYvmzYPU?ryDp<EETkr9)If-CZoPGE_pLRI6Q^rtCdey6&)P3<lOnvFxO>WIDQF^kX!<)QRsD%bL`_K)xRq!m#Y6;)|k+_HvvpP&*bu6By)w#|)zEXEWkSxk1b2k^uUjYVyN29Jv(7*gMQ#{-ki=V9Y1K*JUT?k@!fsCGkEqfias;6-Ioa5M;@N~D8fn-1<!p6INrC(5HKbf2bSo_-_kB82ZEAzLu`L!-Hj7;s=~P(`1#a-m|SMNWhf2yDtQOI_X7vMza{99BXT$)<@YRNTj|^%`Fdqu{b@Ec<MP0x416S-oU7Zh_p=S8|ScRfc*O35y?r=((5NsaON1fSZbDxKJ+1$<7mz<(4<?^8KjMRB5s$5Ge#rz|k=9!@@59aL!IuG?+L%9U98w*bDwU^syuRY~C|wpRAaK|32bKFgX)OK`fs@u|G7^J1t7kI6k6-^jz%gvg}OaCsz;>bHddkhP?iTNy=!H6s4}rI76Fy4Gi20E8o3s6pVf(*=`!_snQyoo%~{CvfkGP{>fhOZssNZDE-zVT1|9ANFhK(jEKas=L9bdW$wlv@-@uujg4Zs@r>r3<A;`^uWl)!61kSV`2v4M1YcYC49QG0G5m@K?N*dO%lN~N?sy-RjXe&@tSOPOg3X!}%&*76%Xjbp<OyfzpF4bA+Vr6$lpj8u(PR(ffW)7qu16rCB+Rzfi)Oi>r?>m(^G@rAMgqfEFC68YRj0TwQ)SEm#OUP4>Mzrmv?2g_M)$M1sVqG^YMqVL(gnoX&LhIpyIEOZ+6&Z`);-=c(p)${LV%U+byOKGOpe2Y4(n7p2#nQwI&`r)R6@np3cH6ha9db?(MjKkjUySuS{`hALDeNl%9Vr4b0@lPO%P<4cGsfG7)=Xv-IXrYM@jb^sig@mkx5(I6*JpH22gL~hH6nP<?2b`;?)SGkWkM4sfcg04Va18!q6M1M?h}%_7s*H8c&wEBq&}}Az9U}2$P!>LXlcLHXk*rpkO|Wa*zcc*2GqrudA}Edd#4;pVEfo5yx&$VLE;JV(<u9j`D&yMlj&BNJb1(??y6Wt%PKO*SJ{=FBs|tV@UZ)z1wj5ftle9{s|2x3VgsGk|~|gkwHjfG(Yme9E<S)1)zebX%G1n)-Ql(c(<B@aTB3M?&=KLbEDyyR63dhm&s?<EUPNTK`M&4Wk(6{_H2021a`G|!6eyHrHmcyFvb;X4c(EG9(zOy#*k^$X(p+jlQzG+xA9_M2fzZXi+>`i^XL_aN$rl;`+7~8)0ZvKRv|#4zTwz|Z<7lbfM{mX4!4C?|LOD6RdLA1#%7vk(i;xzYVS&jFk*wT2LiX(xmcGn80fb+^h!%*v2&fYhp9%C4asGga#mt9xQ2YQU{_+df|cM|Thd;?xv?8wk(xA8l^l+GvIN=D?ChF&D0`vZ3@hnAz4}^a*bdwYghVxMBFJ~?XS{7yw7Ca*M9ABqDpz9LNtHgQI4Z75EW4LeF30d@;7X3TS&KCy#x1@z%j!^p$$Monsap-^?NNf+35E0O<!si4)htV?r*e>9n%8d=?~w~O4M4E|39CPQ0Y3F>HFu5zl~rG+KMr&}bcQZmg#SI4Y!B063jOB>0Wn)drqZXY*f@-7FKE#FVqb6Q6&1h=*px>btP4+(N^|Cw3&UhQnr+XPV0u%$2;LS#vqTF<j41NrNCtIL7)HO8Bob2saN2#uoCFG?*#ur&!QR>sO~ky_YpD%rTHd#Mo3Wfc1e5foC|73Vgw&*d!aZ2hnurRy9qlX|ZSR^C^A6WG#m#9$UTjF;eU_@CH#~=^oQ?MZhwaDFn~l}nNNyQ=A9@G+7dRtQj##tKxn|TTmhDJ`<pSVP<Q-Kwmbii)Rl(6f;VfC-HuQ>%-#wp3xZcrCsLWiw81!$jpD(g~8)rh&{4ysJ&IbRDqw;2YWRz<2n1zH5Nq;1Yx`IEn5Wr427sZM@u_No~A6mpJ4<NTjq0OB^n`F_d0R47l59X}M9ObO`v~tj2XKObmBa|>Fp>N5+B9iP)xpmc^=8KKZmJ}K-0;6_xznfF^n+8@Sb%>*DH%d2$?ZXW>YqRgs0ncHE=^gYe+GC5kIXhFdu|{E_JTD^3x7*28f`DtYSvTErdTp5zwgJRkC2DAR6|*vSO>_EH`n@fz6O~{|EhfC3)aJqoeXM1IYrim--UP%pxe{58sHhW%pm4mA(}NQfXi$|rN3l9#w^ch4>w2$Tb}((C(b-H1W@@Bh)hq$~@`L9%f=4#3Yk<CulOp8?6h^pHY${Vj^uin2NEwlipse%a(|(Qw6No%4wy-JwCrLA8!f9QQPPv<*1O3K-UiSAI8I7ygDtHN!leqZ%_t_Bf1vg0)6nJ`a8fh=Z;JI(olD6%VLPYwrdqs1jE}PjxL*~m8f<L^fyYzmXvFe*ZS`+#~drQqq&uvvUZ<pr?WL;iw{^yX{V_HpdT})c7T%n?=+Iu@ePs}MdSG4+aJg%V;rKB4k9VbE5Q(Ade;lCBDz+z*8Gp^`>*_aKkcS~<xDmZP_G`C5uvEM`(`eYMu$5#uOB0HeUVqxFgfo4eW0gh`niC{6PA-sclpO!dY@7P?BRn-bbaSGABM`gGtWTwuQ7lbl}Q1-NB#P`QZTy!YpB~RSY7~}iE=wMqfa8ztwI&GxHI;mV{Q`yM7!x1H`+B$xGl85H>J#K#v2%{30(T?O~L-uT7TyN1fH_f11iC=DRY$C7Ib%Lbs7_K?Q%Gk9j0&s=PvXLUV?m`h<EWcrCof@*z)PyTAI6p(Ml&Wa}&v@Cd(Nsdk1EscI9mtJPSo~a6z`zpecXmQE0{bfTQEkLFwMWgRB~wKN?psToLk|fgGM5%7mrWdeb$975bOJd1Td!u94oFg=DWr8tjdFbX5Nb9hKW%-XBEjPQ_OFI>D;#CXuPn2@F4bgxUYBagF!5d+Obf|K)<zOd?Xs_dN$2eatcviAWu;}R<?U7b%?gOHP!BFtiJO$gE>=wUks(fneXg{kGc{0i0b6Y!arZy?5MEF~r<r23=yIqTO;Rvq2RasU$FnQXA<a`j=*m;34z;@0_u{;iGtMp(`LSIaA?x=!>DFpA%OGtt^1APKS?kNzEP*CdtP2{)Vho?}*}L0&ev-~@^kh|X?Qir7^uJ|FmMVI!J=dou@woDheTyqv6L9nONX5GI*E1auL1CC!i+$s}$Dm*c=V;6W<tSl|`q+KhB-1$$*1QUk<Q2u5SN-bIGu`{88>5_#^y0+52|l898@{3obD<TTmOyJlDCFpA<c1IeP!IYiQRK|IcD%6k8R(s?9>MK}La6yQRIitsU5-YG3{Pmaa{9h5XvgSaP(Cx~mC+i};6{6+iqvm4YO2+enDb+L5IK$35{j@UKf&1BnDI13$uewH9h&==nVmHq<Q(!d3h_kTebLfSgU0BgWkr?`Q#2H+b1QLM88I9<mYBE&ij>iimTr#1dNZ39YBp!_4i(B?G${tM&_?K%+_AQSU@okXHid=x(<I*K(f|AtQ!oTtsu&pQoD;4-Pt4?8M?jZ*f(*0}c%@DobH8#mL$9|cXFd1mPc(DTZ?M7#FAva{R6awxyh}2!X9G{6jwv}RPCpi-4JP_p{erL;W2wR@YQ;U7ic=&JCEhAmNQZTi6Da7QNP_OiPB@RH(aJJPdZ(2|8V#b$RkXBSUR|yeRP!6G=7&F;$COt6P}eb(dWo=C{Nz|&#9RA~;cFm4a!FzsttgeS^RRoV){WfUy&!3-a}#zQc)&`7KqU$j5KIjn&MnQue`jY2JF8tl22{DwVBfsvPG%h4Aa7lbPh|L27(d}_krGH9K4@syOsu|H-ob2p+#&|sz`TRGAEBKi$&!R|C>Ky|V#X(S@y3Q?2wR-eX`{O=Z+z=?EHAQ32f0f6gf<!rLqE4th~{w!bF)V952<e#npj1+jmIfnw@^xlq|wu|1+jIQC5Yh|=*p*uF4V@g$b4ykYzHc4zL|DJmn}y$H{es)RumQ>$)&B+B-`KM*V^G_E`#2hO>WYZw%+Va2S!gFK988nXfS4p`gPqJ3LHrXoRKMWWOE5dB}dVwX)HRh26KE0o$C<6b*)CiT-!1zt-Z{dxNHdx-svSYra`RQ&jefslqE4}^b{1QbqbG<1*gX3A|YwMp2=J)j|kpvtmTp>rzp8mN2__!Sd-G+pv>svAlD>u`Hk5L#X=+dbs|Lk|GK@s7tQHp&jhMph@ar^gLsWqv^R2!Apj8&hDm0itxJ4xMId;8N<rn!;FKCivIPYKw7_Vjh*h2CEVHSaz<YePHmLT-1SDY*B@!`1;5j49((j;9W?yw!=Az-prVdkS?rEp4af}bAa{avy7pBEH`X+Efxu_?l)HU5qjQ&O;yIdR%qIdNxh5?K`X%;u9|MGKfb`VlqB8&_ju#9y%O_o*o;WSjWR65Ki-ZM~-h2~kh+9ducvJE*Tz_lK%aPkmH3$)cx4fLc{Kp|btWdu@2R|4Tgu%MP0El8H;6t-Z+i)3%(OV~`-&4^vT5Aj{4Nq9?i=~5Z^dM0iw$rwVolFH^KSukm`7wyD4z2aRss5>KxoHzk}nf=hYWzyHIYX7j`s<LgNw#JgC66_lLmt50Cc~<NU?VFORU(HIY?b>2~48g6qwrn!d!*uXbf5fDp537TktOL*N*;~*P-lmL3JtyJR={1Qo4yHYUHJkt?!5yZl)bQA?e&@BQo!O<*0G%>qp|5859!y;Fft#4SQ*N2Q%=Gj?og8Y2Jdz4;ce!uCD2Rvbz=$n<DAx8p<}ic>X0D>W%#cHiw?&wh6z-t;e65GB<O99wL!}hBHM-`ez{r&5w(P?Vc6v3N6%1_=d6f)|w2g9-r64;&dUUWxc5`se2!C>yiV#6n22SFy)*4^+;Y$W841rGoo_}f)xkGYUc2P^sW!`m7P=nYMFUzwkN>Y>yZ+FnthsZ=$`{HD!^cF=DTE{GsgHETVt)~j#rmkwtmPk6G15*)T#ddS$Wn0uP(-pe)RV9VMJWP4bnxQG#EdxlR4!ILHC=W2D1?hsZi&d*cQ==r20KwYmp`Vdy`_f};s3h-~7d{UhaV3X3N-Aqq_UBcP=g14vZ%rPV>v$E`80uX&3ch}YNbgL{OP5Vq{1Rl^_?&dpb49NLR}+08P?D)qgAlHbUMU62P~w#XM?G{Xn<N0bb1~hGAx(FBREb;iw92MQOgi`&gz>Vqs5k_0II@<ct9Xy?jB@sXcob!8#a@6-W~L`JM4}Smb&4(F(>sg(F!P~9fdGr(SWYO&xC+*hAd*j~r=(yXG}FNaNq2H{?uJVxc!CmK#_3(3w;3;3M2<Ppg~v+QMzEyGs9JoqoO36NjY8;@mlBguk=-*Wq$NvCu=u<Sm#v{Jr6H=&6<=s}+pxA*p2|TPs>KJ0DxI3R^jtkwiH<Z;(a6Uubps~FHANwgP6EtiAq*{g^%*e>m2=S`Lz-ryQ!Vu9kxjH~do&sCsMbs1M2I08QXkoU*OUu4phJ`**3+O$hHAY3M+wo%dm4`VB0DyvZI}@52g#j>O<Kj5_~xsZ6-{pR7o#{zbURrpBp9EHhnX!5SgNwEVwwP964#ISe-mk+IiR9G<cUh6FM?V}?zmb;V`(nc{^Vn{pfc^drMNpsFi?SPsjr8ww!}sLObAR*OncKY=Flb`%#}9f&Oa=2vm#f?mY^twEGupE|C~cV2dN4v3{nXn9?i_LTX`QgQa!HA4&)JgVcY~MJnlfw-#`_D3fno2vpO9b-HIw*Et=sfG3Jp~gDtg9bGsZsr-2lwlVcbyoyPGk^#tm1s@G5JrN{KH>uQX0Q8h_yPy{~*h|gq>{E+ZZ<iKMJwRD{ys~6VmU&%ZuMRTN4Xi_wLC=y1}d!j_30gK5?IR8!)k5;!$Qs*zQatmDCp8L$SMyW;$>58^<yD3~gJI^mG^j;)Mnk8oXt-2R=L&@gfTTOQnJ+ojvLsO6sr`l2lKfQy9aqVU~s}PG-c$!b9Yz_5FY;Uf1+ak5>zf^)JH;xufW>pah;qWSXgbMkja%1<Z$YfjjWK#!vgQ2D9M!7^N!WIaaSqxh(_o&duSCc{4nK<>cP7+dFcTi5vHgO&Wbwf)p5B+5=k0UG=>jP8S+%juOY;LbNKrWOg_ln`T3P`EGzSBy3eWxY0L4)Wj4cidXr9rX?$lIOX8zG&n9jriDR6EGl!}h!bE*dDWoh*+P!hk1V%wOTkB-FUKJXG3fL0;HcGcf$S!g!y)qH$%tSA}t&dVdt>SQfcP36XAuRje=^aaE7v`NQ0xd=$q(IBz>uI89cNE%8q!5gn4w)JBub#BkwR#*bA!_+V9(4sVi9tQ3Pa>sk}sL>h##5|q-C^n@!!1}WsB);hY&VYwZ8316RDAR*ys26Nh}eRp^JK^2jS*x0EvmV1eh&lRj`vDBWzR_W7muz~z8c<%b)0{Xon&V6_@SZZk$%=;%lNJds(h@H9$O07{NT0;{>jQ6S)V#&%nY!GK&2v(urdm)}K8>88%d68@~Weiu1ahHpz&$(vDl^Uip^EcyH)}rNY+Y;#!nU)e(Z;Z#@5+FU!3}-yQSi=7Q0E~6JAO'
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
