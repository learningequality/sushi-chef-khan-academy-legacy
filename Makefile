en: pex
	mkdir -p out/
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite en 0.16 --out=out/en.zip --no-subtitles


es: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite es 0.16 --out=out/langpacks/es.zip --subtitlelang=es --interfacelang=es-ES --contentlang=es-ES


pt-BR: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-BR 0.16 --out=out/langpacks/pt-BR.zip --videolang=pt-BR --contentlang=pt-BR


sw: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite sw 0.16 --out=out/langpacks/sw.zip --videolang=sw --subtitlelang=sw


pt-PT: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-PT 0.16 --out=out/langpacks/pt-PT.zip --videolang=pt-PT --contentlang=pt-PT


bn: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bn 0.16 --out=out/langpacks/bn.zip


de: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite de 0.16 --out=out/langpacks/de.zip


fr: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite fr 0.16 --out=out/langpacks/fr.zip


da: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite da 0.16 --out=out/langpacks/da.zip


bg: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bg 0.16 --out=out/langpacks/bg.zip


ka: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ka 0.16 --out=out/langpacks/ka.zip


id: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite id 0.16 --out=out/langpacks/id.zip


hi: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite hi 0.16 --out=out/langpacks/hi.zip


xh: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite xh 0.16 --out=out/langpacks/xh.zip


ta: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ta 0.16 --out=out/langpacks/ta.zip


all: supported


langpacks: pt-PT es pt-BR bn de fr da bg id hi xh ta ka sw
	unzip -p out/en.zip content.db > content.db
	./makecontentpacks collectmetadata.py out/langpacks/ --out=out/all_metadata.json


sdist:
	python setup.py sdist


pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz


publish:
	scp -P 4242 out/*.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
	scp -P 4242 out/khan_assessment.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/
	scp -P 4242 all_metadata.json $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
