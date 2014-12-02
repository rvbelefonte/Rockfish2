#!/bin/bash
#

wd=data/temp.sandbox

rm -rf $wd
mkdir $wd

cp data/nmodel.wat $wd
cp data/dist.dat $wd

cd $wd

rm -f SDISPR.TXT sdisp96.ray
sprep96 -M model.dat -d dist.dat -DT 0.1 -NPTS 128 -R -NMOD 1 -HS 0 -HR 0
sdisp96 -v
sdpsrf96 -R -TXT

cp sdisp96.ray sdisp96.ray.0
cp SDISPR.TXT SDISPR.TXT.0

rm -f SDISPR.TXT sdisp96.ray 
sprep96 -M model.dat -d dist.dat -DT 0.1 -NPTS 128 -R -NMOD 1 -HS 8 -HR 8
sdisp96 -v
sdpsrf96 -R -TXT

cp sdisp96.ray sdisp96.ray.1
cp SDISPR.TXT SDISPR.TXT.1

diff sdisp96.ray.0 sdisp96.ray.1
diff SDISPR.TXT.0 SDISPR.TXT.1
