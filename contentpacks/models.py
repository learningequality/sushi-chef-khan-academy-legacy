from peewee import Model, CharField, TextField, BooleanField,\
    ForeignKeyField, PrimaryKeyField, IntegerField, FloatField


class Item(Model):
    title = CharField()
    description = TextField(default="")
    available = BooleanField()
    files_complete = IntegerField(default=0)
    total_files = IntegerField(default=0)
    kind = CharField()
    parent = ForeignKeyField("self", null=True, index=True, related_name="children")
    id = CharField(index=True)
    pk = PrimaryKeyField(primary_key=True)
    slug = CharField()
    path = CharField(index=True, unique=True)
    extra_fields = CharField(null=True)
    youtube_id = CharField(null=True)
    size_on_disk = IntegerField(default=0)
    remote_size = IntegerField(default=0)
    sort_order = FloatField(default=0.0)

    def __init__(self, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)


class AssessmentItem(Model):
    id = CharField(max_length=50, index=True)
    # looks like peewee doesn't like a primary key field that's not an integer.
    # Hence, we have a separate field for the primary key.
    pk = PrimaryKeyField(primary_key=True)
    item_data = TextField()  # A serialized JSON blob
    author_names = CharField(max_length=200)  # A serialized JSON list
