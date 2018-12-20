osmium tags-filter china-latest.osm.pbf nwr/railway!=abandoned,disused \
    -o ./三连执行/temp-1.osm.pbf
echo osmium process finished....
osmconvert ./三连执行/temp-1.osm.pbf --all-to-nodes \
    -o=./三连执行/temp-2.osm.pbf
echo osmconvert process finished....
/home/pengfei/Applications/osmosis/bin/osmosis --read-pbf file=./三连执行/temp-2.osm.pbf\
    --tf accept-nodes railway=station,halt,stop,platform\
    --tf reject-nodes disused=*\
    --tf reject-nodes abandoned=*\
    --tf reject-nodes railway=disused,abandoned\
    --tf reject-nodes station=disused,light_rail,subway,monorail\
    --tf reject-nodes subway=yes\
    --tf reject-nodes monorail=yes\
    --tf reject-nodes *=subway\
    --write-pbf ./三连执行/temp-3.osm.pbf
echo osmosis process finished....
osmium tags-filter ./三连执行/temp-3.osm.pbf nwr/*name \
    -o ./三连执行/cleased-railway-china.osm.pbf
echo all thing were done!

