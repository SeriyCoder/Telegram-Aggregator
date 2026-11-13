from telegram_knowledge_base.application.ports import ImportStore
from telegram_knowledge_base.domain.models import ChannelExport, ImportReport


class SourceDisabledError(Exception):
    pass


def import_channel_export(store: ImportStore, export: ChannelExport) -> ImportReport:
    source = export.source
    if not source.is_channel:
        raise ValueError("Only channel exports can be imported.")
    if store.source_enabled(source.telegram_id) is False:
        raise SourceDisabledError(
            "The selected source is disabled; enable it before importing."
        )
    new_posts = store.save_import(source, export.posts)
    return ImportReport(
        channel_title=source.title,
        new_posts=new_posts,
        existing_posts=len(export.posts) - new_posts,
        skipped_messages=export.skipped_messages,
    )
