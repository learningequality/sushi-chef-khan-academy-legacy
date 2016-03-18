contentpack: pex
	mkdir -p out/
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite en 0.16 --out=out/en.zip
	./makecontentpacks minimize-content-pack.py out/en.zip out/en-minimal.zip
	./makecontentpacks extract_khan_assessment.py out/en.zip
	./makecontentpacks collectmetadata.py out/ --out=out/all_metadata.json

langpacks: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite es-ES 0.16 --out=out/langpacks/es-ES.zip --no-assessment-resources --subtitlelang=es
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-BR 0.16 --out=out/langpacks/pt-BR.zip --no-assessment-resources --videolang=pt
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bn 0.16 --out=out/langpacks/bn.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite de 0.16 --out=out/langpacks/de.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite fr 0.16 --out=out/langpacks/fr.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite zh 0.16 --out=out/langpacks/zh.zip --contentlang=zh-TW --interfacelang=zh-CN --no-assessment-resources
	unzip -p out/en.zip content.db > content.db
	./makecontentpacks collectmetadata.py out/ --out=out/all_metadata.json

all: supported

sdist:
	python setup.py sdist

pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz

publish:
	scp -P 4242 out/*.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
	scp -P 4242 out/khan_assessment.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/
	scp -P 4242 all_metadata.json $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
