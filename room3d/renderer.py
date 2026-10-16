import moderngl
import numpy as np

from .projection import off_axis_projection, view_matrix
from .scene import build_scene

VERT = """
#version 330
uniform mat4 mvp;
in vec3 in_pos; in vec3 in_normal; in vec3 in_color;
out vec3 v_pos; out vec3 v_normal; out vec3 v_color;
void main() {
    v_pos = in_pos; v_normal = in_normal; v_color = in_color;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
"""

FRAG = """
#version 330
uniform vec3 eye;
in vec3 v_pos; in vec3 v_normal; in vec3 v_color;
out vec4 frag;
void main() {
    vec3 n = normalize(v_normal);
    // Grid on the two axes perpendicular to the dominant normal axis (strong depth cue).
    vec3 an = abs(n);
    vec2 g = an.x > 0.5 ? v_pos.yz : (an.y > 0.5 ? v_pos.xz : v_pos.xy);
    vec2 cell = abs(fract(g / 10.0 - 0.5) - 0.5) / fwidth(g / 10.0);
    float line = 1.0 - min(min(cell.x, cell.y), 1.0);
    vec3 light_pos = vec3(0.0, 20.0, 30.0);
    vec3 l = normalize(light_pos - v_pos);
    float diff = 0.45 + 0.55 * max(dot(n, l), 0.0);
    vec3 col = v_color * diff;
    col = mix(col, col * 0.35, line * 0.8);
    float fog = clamp(length(v_pos - eye) / 260.0, 0.0, 1.0);
    col = mix(col, vec3(0.02, 0.02, 0.04), fog * 0.75);
    frag = vec4(col, 1.0);
}
"""


class Renderer:
    def __init__(self, width_px, height_px, screen_w_cm, room_depth_cm):
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=FRAG)
        self.half_w = screen_w_cm / 2
        self.half_h = self.half_w * height_px / width_px
        data = build_scene(self.half_w * 2, self.half_h * 2, room_depth_cm)
        self.vbo = self.ctx.buffer(data.tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(self.vbo, "3f 3f 3f", "in_pos", "in_normal", "in_color")])
        self.ctx.viewport = (0, 0, width_px, height_px)

    def draw(self, eye):
        proj = off_axis_projection(eye, self.half_w, self.half_h, near=1.0, far=1000.0)
        mvp = proj @ view_matrix(eye)
        self.prog["mvp"].write(mvp.T.astype("f4").tobytes())  # numpy row-major -> GL column-major
        self.prog["eye"].value = tuple(float(v) for v in eye)
        self.ctx.clear(0.02, 0.02, 0.04)
        self.vao.render(moderngl.TRIANGLES)
