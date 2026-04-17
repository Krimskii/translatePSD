import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import matplotlib.pyplot as plt


def render_dxf_to_png(src, dst, dpi=300):
    doc = ezdxf.readfile(src)
    msp = doc.modelspace()

    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)

    Frontend(ctx, out).draw_layout(msp, finalize=True)

    ax.set_aspect('equal')
    ax.axis('off')

    fig.savefig(dst, dpi=dpi, bbox_inches='tight', pad_inches=0)
    fig.canvas.draw()

    metadata = {
        "xlim": tuple(float(v) for v in ax.get_xlim()),
        "ylim": tuple(float(v) for v in ax.get_ylim()),
        "image_size": tuple(int(v) for v in fig.canvas.get_width_height()),
    }

    plt.close(fig)
    return metadata
