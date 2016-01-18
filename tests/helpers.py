
import vcr

from contentpacks.khanacademy import retrieve_kalite_data, \
    retrieve_translations


cvcr = vcr.VCR(
    serializer="json",
    cassette_library_dir="tests/fixtures/cassettes/",
)


@cvcr.use_cassette()
def generate_node_list():
    return retrieve_kalite_data()


@cvcr.use_cassette(serializer="yaml", filter_query_parameters=["key"])
def generate_catalog():
    catalog = retrieve_translations("khanacademy", "dummy", lang_code="es-ES", includes="*learn*.po", force=True)
    return catalog
