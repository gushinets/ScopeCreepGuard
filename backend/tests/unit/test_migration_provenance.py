from integration.support import migration_digest


def test_provenance_digest_is_stable_across_checkout_line_endings():
    content = b"CREATE TABLE example(id uuid);\n-- statement-breakpoint\n"
    assert migration_digest(content) == migration_digest(content.replace(b"\n", b"\r\n"))


def test_provenance_digest_still_detects_sql_changes():
    assert migration_digest(b"SELECT 1;\n") != migration_digest(b"SELECT 2;\n")


def test_only_crlf_line_endings_are_normalized():
    assert migration_digest(b"SELECT 'a\rb';\n") != migration_digest(b"SELECT 'a\nb';\n")
