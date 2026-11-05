# INTERVENTION RESULT

**Change**           :  perf realm passwordPolicy hashIterations 210000 -> 21000 (90% drop).

**Raw data**         :  results/intervention-{1,2,3}.csv, analysed with analyse.py
                        into results/intervention-{1,2,3}.json

**Mean of the three runs:**
   statistic   baseline   intervention   drop
   p50         237.3       24.3          -89.8 %
   p95         278.7       29.4          -89.5 %
   p99         300.9       31.2          -89.6 %
   mean        239.9       24.8          -89.7 %

**Verdict**          :  Predicted signal is verified, p50, p95, p99 and mean all
                        dropped 90%, proportional to the iteration count.