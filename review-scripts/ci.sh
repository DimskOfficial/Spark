#!/bin/bash
source ~/.cargo/env; cd /data/Spark
cargo clippy --workspace --all-targets --message-format short -- -D warnings -A clippy::assign_op_pattern -A clippy::collapsible_str_replace -A clippy::empty_line_after_doc_comments -A clippy::field_reassign_with_default -A clippy::items_after_test_module -A clippy::len_without_is_empty -A clippy::manual_range_contains -A clippy::needless_range_loop -A clippy::neg_cmp_op_on_partial_ord -A clippy::too_many_arguments -A clippy::unit_arg -A clippy::useless_format 2>&1 | grep -E '^(crates|examples|error)' | sort -u | head -60
echo "CLIPPY EXIT ${PIPESTATUS[0]}"
if [ "$1" = test ]; then cargo test --workspace --no-fail-fast > /data/test.log 2>&1; echo "TEST EXIT $?"; grep -E '^test result|FAILED|panicked|skipping' /data/test.log | sort | uniq -c | head -30; fi
