import base64
from collections import Counter
from datetime import datetime
from datetime import timedelta
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from puzzle_editing import status
from puzzle_editing.models import PuzzleComment

matplotlib.use("Agg")

rev_status_map = {}
for st in status.STATUSES:
    rev_status_map[status.get_display(st)] = st


timetypes = {
    "1m": timedelta(days=30),
    "2m": timedelta(days=60),
    "3m": timedelta(days=90),
    "4m": timedelta(days=120),
    "2w": timedelta(weeks=2),
    "3w": timedelta(weeks=3),
    "1w": timedelta(weeks=1),
    "3d": timedelta(days=3),
    "1d": timedelta(days=1),
    "2d": timedelta(days=2),
    "4d": timedelta(days=4),
    "5d": timedelta(days=5),
    "6d": timedelta(days=6),
}


exclude = [status.DEAD, status.DEFERRED, status.INITIAL_IDEA]


def curr_puzzle_graph_b64(time: str, target_count):
    comments = PuzzleComment.objects.filter(is_system=True).order_by("date")
    counts = Counter()
    curr_status = {}
    x = []
    y = []
    labels = [
        status.get_display(s) for s in status.STATUSES[-1::-1] if s not in exclude
    ]

    for comment in comments:
        new_status = comment.status_change
        if new_status:
            counts[new_status] += 1
            if comment.puzzle.id in curr_status:
                counts[curr_status[comment.puzzle.id]] -= 1
            curr_status[comment.puzzle.id] = new_status
            x.append(comment.date)
            y.append([counts[s] for s in status.STATUSES[-1::-1] if s not in exclude])

    # Plot
    fig = plt.figure(figsize=(11, 5))
    ax = plt.subplot(1, 1, 1)
    ax.xaxis_date("US/Eastern")
    if time in timetypes:
        now = datetime.now()
        xmax = x[-1] if x else now
        plt.xlim(xmax - timetypes[time], now)
    colormap = [i for i in matplotlib.cm.get_cmap("tab20").colors]
    col = (colormap[::2] + colormap[1::2])[: len(status.STATUSES) - len(exclude)]
    ax.stackplot(x, np.transpose(y), labels=labels, colors=col[-1::-1])
    if target_count is not None:
        ax.plot(x, [target_count for i in x], color=(0, 0, 0))
    handles, plabels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], plabels[::-1], loc="upper left")
    buf = BytesIO()
    fig.savefig(buf, format="png")
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8").replace("\n", "")
    buf.close()
    return image_base64
