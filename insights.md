---
layout: page
title: "Architecture Journal"
summary: "Essays and reflections on enterprise architecture, governance, and transformation in regulated and asset-heavy organizations."
permalink: /insights/
---

Enterprise architecture is not about diagrams.

It is about decision-making under constraints.

This journal captures structured reflections, models, and lessons from complex architecture programs in government, aviation, and other regulated environments.

---

## Latest Articles

<div class="grid">
  {% for post in site.posts %}
    <div class="card">
      <a href="{{ post.url }}"><strong>{{ post.title }}</strong></a>
      <div class="meta">{{ post.summary }}</div>
    </div>
  {% endfor %}
</div>
