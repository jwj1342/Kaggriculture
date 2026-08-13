"""The strongest opponent measured here: 4 sightings across 1 team(s).

One top-of-ladder player's recorded 720-turn plan, wearing the shared adaptive
layer from `agents/ref/closer_cleo.py` (see `tools/wrap.py`). It wins **95.4%**
of a 477,225-episode round robin against a hundred other mined plans, where the
agent this project submitted to the ladder places 64th at 36.5%.

Committed, unlike the rest of `agents/wrapped/`, because `agents/CHAMPION` has
to point at something a fresh clone already has. Rebuild the full field with:

    bash tools/fetch_fields.sh            # needs a Kaggle key

Provenance: mined by `tools/tracelib.py` from the daily top-episode dumps,
post-1.32.6 only. The plan is a recorded action sequence and belongs to no one
in particular -- the same standing as the plans in `agents/ref/`, whose NOTICE
declines to claim a licence over them.
"""
import base64
import copy
import json
import zlib

_TRACE = json.loads(zlib.decompress(base64.b85decode(
    'c-qxnO>Z1oa{Ma;p7)^s;D>zUNWCjzIif&OZmfmIV1Ql2fU!P|eKY*uEe+LO)m4!h5&2$mIJcI%S@phOW@KdKm;b%^_g{Yf=RbbE_?I8PTztI!^y%X8rynl<<Cp*X`+tA?uW$eO=P$qh=Rf}E+rPeC{P_8AKYx6<fBX5(<Hgsn_V0GL-#)CiUw`=J;@$g)-G%V!+f!~oy#ML;?%PA&-0#0V0(|r7-EQ~s>xb>>yHC5_+i&0ew7a|i@b$yx?3-hgE=TV?{NJB`IPd8DH-G*7@%-gOr@vh6cb^`gnmT-Xb9-$5@Yh2FrvvqAcXu~#&g-xXo3IP(tl_7jpEUi${lnwCr*@7$9%mLkVcPiFOOIpVyynNx@9*CJ{Po|DpMRTy{0);|n?1U_eX|?S#)`e}^cQ&czkdDUahRg%n}>z)=Wi3nUiS2($@;o|+&v@@e)>cneEfMZR;OM(&GY09-+#ykYIY#t=Z^YQT>_{#qsPL1=ubT8&+z1Y#H7haz4&zh`8X$VoXV4p*6FA>rx(=cdfZ+xI9=y@IC6)V_MU5X#L9Cm512IRs0+i8z;Sx&O=U5inl@Umv;VA&`S_rojed0r6^5qM5;`?_cUxRIdE3z_b+{SG;1r)bHG2YkD_(Hr8F<b=EN|9jn;IXZ><{nn?sjh;fBy6C;qm?5`+s{{4#18m7>4x)3K~TobFy~)rpH^PdF%=uIUTtROlAG#*8Z|SlGQ_@>l>fHsmuN$_u-GO>1fHEyUTND9k~402lLu#JPQ|mL=0<W1F))i=Yz4S9aG48L>_$j#IX5S2iKt#4_1009sAUN%Z#j<%1wcrsx~XTd>R`zjF5B(oD8~_5rU%}3{bsQGcQlxiBf~du6DVNqtUOAT<VZn-Gq}HO^noF0#cMu*<s)sukof<L}Sz8@+kTN9WLN0G`yO9^Xc*7cK_q<;o)z;VahM%X0;tc4wG0nve0C`|Hkz`{nY=SH?HJc6;xmBitlyXzkUCgi-NJUI+R_|Ge~B%$@;WHG$Pv0_Nh6c<AmJTox@hsF_PW{9bj_H^|)Pm56fE`PVM-bjRp+5-OY<?X4UAZF6&7WbZWGI-PI3`rQwvH29XL!(dc1Q7`4qxpQ6c47_w<baa`9lS!mc@_K)*TZUz0@?${=?Hoa~2CpX=@Ir=d-Fl&Ce{KC4EmwTm^fh7co`7zY=WON<ByM6fAopk_UL<3Dn9Ej`*n!xyN{Wb7$dvA!~i93S`Dos8f)^zW^$a%FOg|i;G<23qXW(AGeB)jITFtZ^#0Tjc9?N4&a`4~@gb?S3}xbs-W4t*yxM}2IwUueH^c@rzdezt^S*^v_2>V3_vueEQVmGKp9B9#d=@cduiKg}$#?vQ`zxAr!$TKJ-6xP#C_8%7!}KVzgdXIf^}X=99RoYBQSTz^lWns&_Wxz7Pib!Dnl?#zU9aX!N3mX0Da{YN1tl=Z!R%lHjxwfC^xavDvWH3Vzh0CDEApWWkvUB4fqw5cLWs`G+h`P?Q+>(rk4EG4YXCC51ERY!zBN3B?RYM#imx<0gB@2>4Y@I;qU#HS(h`0H#4WRW!(PUuvsN5^D1G20X@`fkOUI$LV4afKcitqJLYZy)YI#!DhMBu5+Y{{HTiNC$6^A(QUwCHWTI7N}<k(7_EsF7?`Rsn`AyVOrVTp&lMMEI9Kesq-~@K0qp`MvIyAk^5&blg?eM<W^Q!i+hR-243~HAp7a-edeU@`iZ^k%uZOhfkIDj*g$7LN_LH-WAU~JE#KxS-0P6KwK2z|L)a3AT^l(-Dgsvc_&jhKZi3)3_n|b&=3#iAF-tNWxQ%JKlQR)|SW*Ab{Zl~{(fXTROk}tw#u2l-LaU>&48c`~PcUIUPA~E{104<+TYr@qB!NyCr*&3UJHZ@<NhvLWEbEF*f@Tb@bzsm1%e!goL9QNN(8!QQmVY0jSAr*tHWqP}oYj;28YGObFdy4?A38s$CT+NC0^W+~gR2>f&^nvU64AS;+cK;TINH~LPT;<REs9Cfz1YLDxJWV;I_p#hq>X#3$D7qpK=+_=E%<G4lfa6w{k4#>vT1T33xR+Fm0-ld4StLu9p7(BJx9?6WX@LR1g{$pN9IJG-3r5?iU|Aq&?)I&@$zhE&dAt+4jeGtyybK0t`EyU%j~!!Z@6-h!?`*wt3@OlA`^Oee|*7pqraf*d}fSwiolFx*1>q#`LrrU92)4c|Go&3DKsPJ8$exo&@F++^yuZo+yG}^TVNytgbX*#AE+1&<mG{-#?R||;uttGDE2g0vujIV&RDxKf-@SSV9iB|FFjAe%yypGN$nIhbkJddPM)i|O>uRoD~O@jLcpv8DJhS$c9#On-8dw0wv=w&F-FWfXn?RaUuN~HQ#`B#MV`2owVZYC7p+5Eh`U9Nsp`4yB6u4uF|C|z!aRuvpTeP~;AWtevOr!xG-U*@LceL)L4JKG+q<~Q4OA+boD`%A>50xu2^+w{K@N`@W9qPyh6T;nPD2_yoPNPhMYg2Y3?r<>45BXNJor9jhfbF4j<cm2;%pG@&z<rfVKr>;V#QSMGi%2PbYbv<5M1_T;7WpBF#d!76OUIQW^p{$e|mrSSJiyOw;U!q1|DD!&kmVlXD=a6U}JuwpAk9QEBq+!kPD$&vZg1aDqip%+EFJ%x7IuMn=$%sCOp_@^k>vDh{pvBh=rWr)l~ykaaxMwx_5+W9aC9cR|-YnVd#qdut%E8ROnBCnb3a5EbEc03&Boc<UmHrUUN2$pDq^9h_l_oOEk+vSfqEz3`1~NgPVzlA&*fSBhiFtFn9raL<kZc7qrmljl^b6k9SsaB-%`P;Zc8?IZ2-Dylr!x@xl}ho}eU5UU$fe5;P?sVU4r$o`YGkcm&uCPe-UOtAF0ab0-084}B6Db<TC!=ZhkUv*i^;@X(`f4M;rn?ZWK9otDORw6(tD>>&;2CMT)K1>r<dKvauHAnc~W+UehgU$BsHUZ+T6sjA!}f`UjfsQA`NU@|GvC>F0s_ee5uCCr)-2!`*6odiJ{*3J2zxk~rMWxk=Vme?5trt^0Ov!hER*|6xNlaDT9X2iiGV0sGELlgl->V*LpGCJQ7FFfcT1tnE<rX=+0tXy&nDnh+1a)B>rFMf+n7`Wnw;|3xwLN9Xk2G)gBqxHiPW-eGVoT#AzV4i|c<l#LOe&fS11qqdvn0p&!VL(7SzIp`4r=I(g_MB82RS`yYv6jo-^~;}bL|WTFiRBx*V4-P-vI>SG1G6M&vvq0JxF=0GU?)ryw~U~gof=k#Diw<`JtP9qBuUb20w$Lt!1M>`Fo>;_VX`#M<w|kzYcn7w0Kc5!Y3?X@q1NWyOD3!yESxe6B*~zztZPbN01$5@eMbRXa=@PmUsV!6DqJ6mlIEJ(6c5L7)U{^D5kLoRLl#G|Ln^3UV?XGa{z`0mHuwc?xRpDIl6z|IJ$PO><l2+r)~~Q2tW#$!vCI=0H6o07l|5N1bU>m6dHgJ?0pG^^k`+g5pXLW!lfFE`F!GXsytQS8uVtLH{!BJ6<=~lzsmdqonfCsNcJEnd3aYwc(g=*&28y|kcR&30%xqa_U#?6D;KtO&3Iu{-A_zmy8SA@4JxMETKPGy&HLN|=g<ONrg=65saERg#)2c(_cQn(U3y19g(_cCvxM1_h8JKWIFsQ<|eH~@z$bAgR;W=Z|%__-@KcE4G$rP#%0OPlGWFs-9A6cu4Dt$)zpj!BtsbdLa%gz-0L_o_IS3OH11(>MDm}x!MZM3DJ>lV;4f{jSPk?)BqS8Y<>`M#5u2OjY_13xx-1f3n^P*czm9=~MP?1Pxb!Gldl*m~nEnX^mG^r3P6;#RpoWQ1vqtCEBxPG=$vFmfgr(y!1W1Y&9sHn$SwhKEijzrLpsjH*|3MAWgQ#*C?R2U=@4R!u07!}QvcKotc1Ms-a`GlbTU=k4~71t2WW1?ZtLVMhI-<hsFZDJZQuAD=b&Z)vbc$#=`dMr~yaKm9|bLKA+88=J}5^G(5hhlaXOa%z^UT$XF=<q6x#okn+cx5@#6Z=8oAj2Nvx=y`k*p9Wnh?{#@LE@qK)Pwe24p|HRrg-LL=(Sw0cHtE=vCZNaVsUGzPP>BgkE0A0G2=i=QD_C1U<s(l2Z;?R?SR=c5Im^{TdT4V5!G%)!jdszHvFDd2rGgZ}g^H{c<SlqA1<%cF*Kbr}!u<c1if60uFN-PW+;il|qyHl${HF!KJv?LNx<lvHq?g8uuWLUx-B*SqjZOEcI+wlx+VVV0w_5j1JaywD?3^a}0*Zs7M(gBU?o>f{`t_lcvNbQ5Bo{puEZx>>yhhZk@Poq6JL9vW&~}KUu&$IDQhI?d77XtmsYRPcVXx-mGi7sC#<atj%Xu6K4V{_I;l{c!Pc#q6Ko^x|-<Q1+x+O&mzu)lS7C}p%h&q{srdpLaL8*v&dF31?q8cXb-GKUkwsD%T>zW%J3I6xVJjko25v5XG(GZ-TJ=#K|wuydy^IUE;=a!Z2;#&lk_M39Tn?^CmZUscRtJ)<TvC+$rhCXA)=Sllde&@<YS|BsOsu0>!&+7&8x=HT4;8|Ps#wH@6H<K=KY^{M5j+}}*DV!8Jn^3?h!7GaXZVQC(j?$22+<=9GLzJM8R;8mp4_!D)Lnoyl<T7fZrtJ36CTOpU>QkZAx;ZQx0_6nWX8X?AOlIAvz#8O>rM|z=>_^&_jB9%`y*h5SRGgjFqNpY888q2EFFcWIOfyO=8eoKV&YAK#<JX3#h=OGvv1P&YLUfb>)mYTbD7L7Tb}noTPN=71mnpxzc{i|8H0THm<F)i^I2*OWDWSFaw6O0=WF9e?Y@`!H?N)*{R1)ZS%EVb1Ux%8JwqCTx7H74cjxI@ENDRv0$@F>2BhP8+YUrp3HXtk7JJ@w_-4>nkRhu&o&GPl{U9`f@t8On$Q6`i02$FZ!XA3;^P4=Z!`Xcz-%kaFJNFqmrE*9GM;0XWhRHg2^hRVf=e$M38AdY9PlR<p%Qiz{P5K^Tyj=ecF08g3MtPB{&Mv38|d$q*kJj-c7K?<#oouU2Y;xRc(pM^^UBbj8tJM7R7DlKrRbqWGpD}vW$KqEbpPy~s1Qb30s2Snetp`;_mpl|@v0%zmHfUr$0M|7=5gOxJw@y;$){b2`VFVrc3!J|`*;u|c}LR@WfjmSJt7e>W{a729TM5|kq9w73D?Ys?2KiG-KyS}_&Fd!OYc=K7D55{*hXg+~?esi$<NX`Pz5Q$2P2IrkBg(fGN5<xzGNbn*L(T+mN@sJkMCfApr5@zls3B!<7^dtdKm@1O;h&5!vIABLA;+_&ta(fan1%ohM4E!+eL{efxIvG~mb6!L2wTt@F@S;L#8y$FjI;msg9DWxO5SM3Os8`|!)r2A!lvVg06Iv=&YtMnbke;(-wo4Cn1uO5REswpzp-G%BDfQyI;b@043*7Ot`JQ#37AhCyT+n?BZ9=Y`ASqzwp%s#XJij1ZEL~l#mOcbi_3Duh31<@{QF%q?R^PqH%B591nTziUEv(E%B8PaT6>n7RXpkOIk0*mrs0Dga1RpjL_dc3-FDs|Z7!ubb*KBY^(wyz4x0Fle5gsA2*Uw{LThY^nuNUSS-eW;$9Y;eQV!q$^JCUSCM%YD16Ioet<2b|U^05T!CJ`PSd(SNhg{6xPU0H8WPtQd$&qA;-RP>b$XE{~`4NXEtM&8wA?A6Ide(#tufHW1Ia1RWHbyY1<*srmWMDj-x%5bef3EJU#^Kx=(`to;PTGa$-#ihKOx{80m-EZd%?mMTW$dY;1dEeN|ewuo4Y{}_PWwN_AzwG+Kt~o^&l+aDjDu#NhHHVM=ItG<su2a7xN@gK=!k!gOf0kk<42@SbAC^(aw6d9a_6aokSwMQXG`d6JrOcR;BC}-;)9s;wekN?=Xwyic*s7lK%BHQ-#0-`k)~C)ON#fYcg&_7ymI)VT?5i!cC#)T}7=+8js*}lNiBdvZChMhH=10zzW7R_(t|BE8Ov4Y`7Boo!Z6b7(o8eP8s#j`a0My93)iK+Fc(FGJzl?|gGp7}tYJ*#iLl{&5QlSK$o+HLX?yDh2i#k_HOn~s9<SM8v`%0`1+7yfnimMDiK;kWJ^%^F-;q{AC5A`dIE|quHk#~`5b+)8bk+U()I0{pwOzwoJlaiw@<J(h&r)=GnB0HpBYhz#IYRe5@A{mNnMG*Zwe(e#p^nwC`%q_7rDDmu^D#<gvg{n`qdTT)jdz1iWWp(9}71+-{jf^^N6;V@`H5G!$p=(4`ShR3gvmz=bu;dCcG()A2LV@6ePDa-X%x9vOg5H-jRZJ<An6-Ju3oTnEIvB%p0<#)zuf+@qc1BsH@${V5vGT(4P*_H>S13KKXCAU#&ph>#&K^i{4>S$@$;~qx;AWyaSaNo6UIsDAU`D=N_1=aTLw;!L)vVn@A7UY~h%g*f9c7?+M2yh$&a@;8)h(CSk!6yx+%nE+YcVN#fVzQ(2(A8j*vh5~o2eY@4=%Xq_#l8^$A}Z1FJe&0$4A13wjv3wTZn+6f*l+tWWkH0PU{m~-r^xZ#D$acQwyjm^+}vUsMiw=sGZGMhlZ-O=Pa#PNCfz*h^gU>3y!%pRKRM>%<3c3w7vR6R4by8;pL%4bg7BeVQCW=Ib`H(mwKH88%*n!l|Ln5rvoZV?9}VVvProcohRK|5pp^REyiDTFL^1zLJXhd2gEE<HHO1!-`(AR`0c2-r9TaWutsOojk6xYOt~fj+NpuEDXYYzQ#cBfChIoIrHYA~M(BEm26;!yWj)4$iD*4E(%^rNnEGHi;fl!(!Q&EGsptdo*c7l;LTv+a@$)my6>M~oLhWKtZrgxY9bh%nNz)3K3%gk_1cpR!VZ_xyRmedmc5C&@?iXj?kenhzOFP70x+LDE*m32^3G#oGRZ4mPVS1IcR)v%heU-`PA(MbEr70)9oHvY8C1dQJCU^5tx}=QRu#^pIaPU)N#Z8(T*^>5(6<Kjm)H}bT1O65YJ#kSq>et$JH;AlzK<+R~G!O$K^hi+7<-Qu6=9hV{vSox6pmNtN?x<#_LK-GCAX1K?M~I*q|GGHe=~}-;h~evl+hM9XhQ>xojy+!tX*zT+ordlOEIbwggX?ZM?ds-y)Q^*~?aY2`Kw=ruxfONQLPSn3?wkAlP$du7pLv#Ab!)2-ZOAoHEwiXo6jSU>#_UU!gHDf-B1nHN(KCDLH3{YLnDlSn-jw7puRgJeq*Ktd;5=ut^5JiOV<r7AHS{!nZ!OKptL+nPd1|kD`Ka`9E%oE%%zfU9oh(A1hm`s#dmxZCR=iI;Jg)tF<lYhQC86dmyX|?UFivQoHeDMFR?gt(3K2P{8u7}bRj3?a$V2+^^ZUEEKYz8s9zQ>53c@r4GVc@?G4akV=q!AF#+%*LP;({qkYfegewv$xG}`0K@Y$8$%n=`egVy=<h$#xV@>Hcd^hz;wXhJ{!0Y%QV6R$4pLDGta#D57EOks*9)r<g0=D{$CUY$10#2}leiP$RNub{In>h%UoMy#LeTsKnP*HXduW7*4X8#N<ZlEd5^Y4HN%a1lKnPLA2@9z|ZkA+P12iC0iibZ>|s!;+sTKr*iXTWB~Emb0?UDBzegJoDK1R8@4mS<cRmZ8zL)^QxIK*jSHpNz&u8btN~8rbXMhO&cqbf@4yqO$Mg5<x%DmT?RN-)>K+`V-S+Mi~=3d6&iE6fH)1S%phW*DhbP+ZK|7tnKjM$Aqqm$L%0fAdLr&iodY6Nr(#)6+Y_tJf)FyVQI+RfHf=#XepYn`wZ>VqsGgI!9B0XS#j!O>t8R#MsnS*K;#AtDmj301=IScbtSDNZ70a8GmP)J)nz#(DbXPL#q{=HeT-E$zN12i2BBzKB1J<5SJwcq&i*JxZlBKrFRI%tv&8tV~j(KHck(-L%S-IO<ug@t>Adk$!B?|Kj3j+!kDN!Jcop<i!ONMQ}77cAOj0X@Qw)!$u_1sCb%GLHzMTV*n{`TcS2)!!W)l)-bg~sj>!(}VP5Ipxv(LCL$f+|&PqEt7J*pd1F>EK08f)HDEyvSb61z|}bbi7_-fj+0;vcMMYQP>X;sdWc47zF=x9x!+7KVBZ{1e5@>(#(IyuqIS`)4`sz<F!byEQuJfBq*Bd#8xfB$Md8X3JJUs)1@HnhE}{o!H^ltISW4!$Dj^vmj1zlw<IEKd-0Hbl0zT+oJ(&I01d67{cgG1@-aAJWs9(^JOkgX3)c$_hTw<_lL8rXMAZQeF*#c_2(bYTb{EO;AzG-FQ$`H>hpQ7Ftxic*AwH+(B)X-0@jkT5KI~x@T3J1U9p=IrG|_awsdK4_ZZNgJF!2aIKR;+1&s8@PK|)1xRweWGnvS7#i!w-foTwgMHNyJiD_2!O0cz<jQx4M{B@CJuNJj-1(3(%GrB+O!@N^kC=K!Hpx#_Sg#BiD^nl#3aa*GY>r&!!T)J6FH?3WdYTrH4+us_(UyhsIVJz*=HGdwrXS(u^&j*12*{=Z7YyOb79LD5ZPu~C-8uBQ7nRTgy_ScaNf2Rv4Qs#Kjgp`*(sAnN5rZSAhb0M*E_=aE6|@#@lZZ7D{?mgA;_RZ$?>!@gxti-}U3oo0Pdyu{$hZ4PF_1T6uOoI9l5CDCf9oM@nTG^d5;dZ9Ut(Ftedn;zPjL?$Y@2Sn$RMTuW&j&7`orf4ENpc@guHuMB8ZTcl^MzDRHcvfdFCjN+ag(8Vw+sy_)GsDc4gxbIfNfVeVn|q@cA>^pnD8G!AK&B9ErcU1`-m@3=W@>VLtXS>jP};^tN49o(j<_~KoiU4#jG2O>s$VW`f2L#LRP^L1O+9hUsW-7#wRaT&n-NCQKqIvvG?1rFJj^lrq*X7`oBZ0Y&tgbN<y0BS=8N?iG>Gz5??S0+ABeOEGm_R7DqWpnHo<kv1xcT?45<M=S7>tEBp@Jj;x-C{tOpV#^KWW&H^v(`TPw3-IFZe0Zer&zM^+;ldO@!&`@T|#cI9ThVb-0I=EOkB+yL#Ci0bjr43ZJLs(KgxO!J9&LdV_<0+s`Vmq}rpZor0KYsg@i7>eyy)aDwGh!;UE<=aXm%babvCmPJIL~SXXj}`md8GH<z>;_H7d|wJ6mCBKk%wb!na3!PCY^RYrqC9-GBu6Sw=5cDf>W~C+ExWLvDCjT1+jM3~Nft|*XrrBI409A@Vu<)3VMn)-J}5069=4@aX0NR7RU->)&yZYrEZ2qoYujJTnhMT2uFFaChw_7(mbWOZ#@5q~u+GSR!>F-&(t23rIkt&BS!)9Hz)dH3G&w3H0HCB^)e(`_$}iw-R8_63Xha*+DVC9FsSN5XKozlO2A(zwUrAVTo{hSEhH6J_t-s3EMxt9Wy0m_&zSiQs7O$#Od^3N6)RpaFDfKLUItF(6uBrw3OmbQV&z{_&UI#aa7a+qW&u5yL*~b0SQ*oFGh@iFI2ZPKFO3JWM*c1$JEK9?(b|OGKtTmLv9y$HJ#F`2NU5&V7S^6tZ+_Ml$f<S&}AF7oSEjk<*0o#l7EkcfMkRrt`b*U(hvNyC?sZ2=AV6*cVpBN2L6q`bHfld|qltV3ENS!E$>{4-WO6u|NRdTz_=A&}Zuzyrb9T;e&xM)2fAk;q$%NqEVnZ47`)rn}ykz*hWC;72b@eCy`hxBvsn`ep<CU%?fnA%`rk<e6HQW9yB8ralu9lcKj)^Ku0I7675s09PWV(c)%4)P!69%}MyT=T5rJQGjSZCXv7tU;pf`*nI9Thx~?NAJA?fWbap_s>6+MU@3wTK3~jj+2@Ba89;iUj4WrCnn%o=SPevg>5k3$`MtfoY71^b9BsjLJ3!*(%KEJI;SQHwM<E}Wz(vrd=v!YM3;V3;rcrIL?o{FRwYAq*7_y!2-;=LW7EMsU0OTORio5Xhp?A=_!Xjpnk*LctkAMggvAT1HgW-?0H*^}H(=fU)-}_BbW;;~QZs=F3-}04WM`?&jNRj;C#w*rw6c1XZX$Bym5X!l)X8Bnso-4k4;d7p-m8@iAWVZ~R#e?EDUF6yzT@_ha8_{Tgu!z~mKRk9c0w9xj(A*&&|F}$7OZOND>tJC6Hi~Ql|~?uy%aNB*=c=B)^QGzjg`Q#wdqv7KO>`mzXQZbAZlEm|Al0b^7#@=Mx;Zowk{7-$gKm(pN9^NqU}{*tfi|Qeh*?%lljD$2tsw>3_V$;59yKWz`fzfRS_NLj<zas06lPoaJLIWZd7B70V7tTjK{qe1)_zz#({UpIAysZTNrI4TgOX`R2j>?RtQnLz=nMGeI<a-^^XMaLQSfyjGSLZ81J#7`%U$=oK$ukWR=g@B2;EZ#B=3eQIJn)*33)q#>&I4{!FkW%r7MONd^3(l4+caqDby*(Pw(|rX}`bp)}Mw14h(^t%za_BUe#n7@5t`CK;0vJd%ZwtKeu_D`L5j!Qe)0L3SBH6>n8G=#)Yg9<Vo>D@-zFSe*Zy4+i{6!~3;k^$Z>7!eLpt$AXjFCmSZw0IVkVsQD`SC$$D!&Nn%3vMYCiRvY3pQ@B@Izb-dRu`nbzT`f&O0vPetz+i<Y)SO(Ms8xwNW5wjBA%whL%xIAs7Nx-w3)rzkRUtB;z{&;Q+`<Uz^?k0Tx6Za<6NQG2BV8_x3Na6t+#GDNjt+{xP7V2bn+1}onQcSJ1&vgCx}z9{JKrJATrW}1*`Q^(Z7hI1_-z8-N<fT4OC|c1w5g=)stu?nnRRtt)3$LXLadS~frg#=Kw7Ya1dx}HEBm|r35CUq_YJAFM1E;PVi3|{b`Z;QKw)J&(udgWMr$2We*t}*y7^Usf7S!YV93R4;h)U@nqT-xOKq)ALf)_u*aE(Vl(<=f1dR-@VGn>qeS9->sPhneUYlqfFO@v%jqOrbtEz{xG-*2pDZ+1Dhr|B^$5cQY'
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
