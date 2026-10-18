#!/usr/bin/env python3
"""Render the approved Omayed cooperation story with the current package workflow."""
import json
import publish_four_news_20261018 as workflow

_original_body = workflow.body

def body(article, language):
    text = _original_body(article, language)
    if language != 'ar':
        text = text.replace('؛ ', '; ')
    if language == 'fr':
        text = text.replace('<p>Sources:', '<p>Sources :')
    return text

workflow.body = body

if __name__ == '__main__':
    workflow.A = json.loads((workflow.ROOT / 'content/features/egypt-uae-omayed-20261018.json').read_text())['articles']
    workflow.run()
    print('Egypt–UAE Omayed story rendered in AR/EN/FR; Updates and Land & Sea archive, with the existing lead preserved.')
