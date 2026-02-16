---
layout: page
title: "Selected Architecture Engagements"
summary: "Representative programs and architecture work."
---

<div class="grid">
  {% for item in site.work %}
    <div class="card">
      <div class="kicker">{{ item.domain }}</div>
      <a href="{{ item.url }}"><strong>{{ item.title }}</strong></a>
      <div class="meta">{{ item.summary }}</div>
    </div>
  {% endfor %}
</div>
