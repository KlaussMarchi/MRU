# PROTOBUF

### Diretório Desejado Python:
- **release** (mkdir release)
- **plugin** (baixar e extrair tar.gx em https://github.com/nanopb/nanopb)
- **telemetry_pb2.py** (será criado depois)
- **index.py** (código principal)

1. Converter o arquivo .proto para biblioteca Python e C
```bash
    >> protoc -I. --python_out=. telemetry.proto
    >> protoc --plugin=protoc-gen-nanopb=plugin/generator-bin/protoc-gen-nanopb --nanopb_out=. telemetry.proto
```

2. Pegar Arquivos Convertidos
```bash
    >> mv *.h release/
    >> mv *.c release/
    >> cp plugin/pb.h release/
    >> cp plugin/pb_encode.* release/
    >> cp plugin/pb_common.* release/

    >> mkdir ~/Arduino/libraries/protobuf
    >> cp -r release/* ~/Arduino/libraries/protobuf
```


