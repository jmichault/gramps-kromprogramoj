 les fichiers python de ce répertoire ont été générés avec protoc.  

les commandes à utiliser sont :
```
mkdir src
for x in api_app api_stats api_saisie_write api_saisie_read api
do
 curl "https://gw.geneanet.org/setup/api/$x.proto" \
  -H 'DNT: 1' \
  -H 'user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -o src/$x.proto
  protoc --proto_path=src --python_out=. $x.proto
  sed -i 's/import api_pb2 as api__pb2/from . import api_pb2 as api__pb2/;s/from api_pb2 import /from .api_pb2 import /' ${x}_pb2.py
done
```

