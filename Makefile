contentpack: pex
	mkdir -p out/
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite en 0.15 --out=out/en.zip
	./makecontentpacks minimize-content-pack.py out/en.zip out/en-minimal.zip
	./makecontentpacks extract_khan_assessment.py out/en.zip

langpacks: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite es-ES 0.15 --out=out/es-ES.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-BR 0.15 --out=out/pt-BR.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite de 0.15 --out=out/de.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite fr 0.15 --out=out/fr.zip --no-assessment-resources
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite zh 0.15 --out=out/zh.zip --contentlang=zh-TW --interfacelang=zh-CN --no-assessment-resources
	unzip -p out/en.zip content.db > content.db
	./makecontentpacks collectmetadata.py out/

all: supported

sdist:
	python setup.py sdist

pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz

publish:
	scp -P 4242 out/*.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
	scp -P 4242 out/khan_assessment.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/
	scp -P 4242 all_metadata.json $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
