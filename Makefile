contentpack: pex
	mkdir -p out/
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite en 0.16 --out=out/en.zip
	./makecontentpacks minimize-content-pack.py out/en.zip out/en-minimal.zip
	./makecontentpacks extract_khan_assessment.py out/en.zip
	./makecontentpacks collectmetadata.py out/ --out=out/all_metadata.json

langpacks: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite es 0.16 --out=out/langpacks/es.zip --no-assessment-resources --subtitlelang=es --interfacelang=es-ES --contentlang=es-ES
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-BR 0.16 --out=out/langpacks/pt-BR.zip --no-assessment-resources --videolang=pt
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bn 0.16 --out=out/langpacks/bn.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite de 0.16 --out=out/langpacks/de.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite fr 0.16 --out=out/langpacks/fr.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite da 0.16 --out=out/langpacks/da.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bg 0.16 --out=out/langpacks/bg.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite my 0.16 --out=out/langpacks/my.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite id 0.16 --out=out/langpacks/id.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pl 0.16 --out=out/langpacks/pl.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite hi 0.16 --out=out/langpacks/hi.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite sw 0.16 --out=out/langpacks/sw.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite xh 0.16 --out=out/langpacks/xh.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite kn 0.16 --out=out/langpacks/kn.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ta 0.16 --out=out/langpacks/ta.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite zul 0.16 --out=out/langpacks/zul.zip --no-assessment-resources --contentlang=zu --interfacelang=zu
	unzip -p out/en.zip content.db > content.db
	./makecontentpacks collectmetadata.py out/langpacks/ --out=out/all_metadata.json

all: supported

#generate_dubbed_video: pex
#    PEX_MODULE=python  generate_dubbed_video_mappings.py

sdist:
	python setup.py sdist

pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz