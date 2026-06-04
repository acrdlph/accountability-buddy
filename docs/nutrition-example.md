# Nutrition log format

The assistant stores daily meal logs as Markdown files at
`nutrition/YYYY-MM/YYYY-MM-DD.md` (the `nutrition/` directory is gitignored, so your own
logs stay private). When you tell the assistant what you ate, it appends to the current
day's file and keeps a running protein/calorie total.

Each file is a single table plus a totals line. Example (`nutrition/2026-05/2026-05-11.md`):

```markdown
# 2026-05-11 (Sunday)

| Meal | Food | Protein (g) | Calories |
|------|------|-------------|----------|
| Breakfast | Smoothie bowl (half scoop protein) | 25 | 500 |
| Lunch | Tofu (big portion) + rice | 35 | 650 |
| Lunch | Protein shake | 28 | 150 |
| Dinner | 3x bread with cottage cheese, hummus, tofu, salad | 30 | 850 |

**Totals: ~118g protein | ~2150 kcal**
```

Notes:

- Workouts are **not** tracked here — Hevy is the single source of truth for workouts.
- Estimates are intentionally rough; keep protein/calorie numbers conservative.
- One file per day; the assistant creates it on the first meal you log that day.
