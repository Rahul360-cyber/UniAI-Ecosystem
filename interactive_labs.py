import ast
import operator

import streamlit as st

from breadboard_lab import render_breadboard_lab

# Optional second IoT lab (smart-room control loop). Safe if the file is absent.
try:
    from iot_lab import render_iot_lab
except ImportError:
    render_iot_lab = None


# ============================================================
# COMPUTER ENGINEERING: LIVE CODING SIMULATION
# ============================================================

BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

STARTER_CODE = """# Temperature monitoring simulation

temperature = 28
threshold = 30

if temperature > threshold:
    print("Warning: temperature too high")
else:
    print("Temperature is normal")

# Simulate sensor readings

for reading in range(1, 4):
    print("Sensor sample:", reading)
"""


class TeachingRuntimeError(Exception):
    pass


def evaluate_expression(node, variables):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, str, bool)):
            return node.value

    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise TeachingRuntimeError(
                f"Variable '{node.id}' has not been defined."
            )
        return variables[node.id]

    if isinstance(node, ast.BinOp):
        if type(node.op) not in BIN_OPS:
            raise TeachingRuntimeError("Unsupported arithmetic operation.")

        return BIN_OPS[type(node.op)](
            evaluate_expression(node.left, variables),
            evaluate_expression(node.right, variables)
        )

    if isinstance(node, ast.UnaryOp):
        value = evaluate_expression(node.operand, variables)

        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        if isinstance(node.op, ast.Not):
            return not value

    if isinstance(node, ast.Compare):
        left = evaluate_expression(node.left, variables)

        for operation, comparator in zip(node.ops, node.comparators):
            if type(operation) not in CMP_OPS:
                raise TeachingRuntimeError("Unsupported comparison.")

            right = evaluate_expression(comparator, variables)

            if not CMP_OPS[type(operation)](left, right):
                return False

            left = right

        return True

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "range":
            args = [
                evaluate_expression(arg, variables)
                for arg in node.args
            ]

            if node.keywords or not 1 <= len(args) <= 3:
                raise TeachingRuntimeError("Invalid range() arguments.")

            if not all(isinstance(x, int) for x in args):
                raise TeachingRuntimeError("range() requires integers.")

            result = list(range(*args))

            if len(result) > 100:
                raise TeachingRuntimeError("Maximum loop length is 100.")

            return result

        raise TeachingRuntimeError("Only range() is supported here.")

    raise TeachingRuntimeError(
        f"Unsupported expression: {type(node).__name__}"
    )


def execute_statements(statements, variables, output, trace, source, depth=0):
    if depth > 8:
        raise TeachingRuntimeError("Maximum nesting depth exceeded.")

    for statement in statements:

        if len(trace) >= 250:
            raise TeachingRuntimeError("Execution limit reached.")

        trace.append({
            "line": getattr(statement, "lineno", "?"),
            "code": ast.get_source_segment(source, statement) or "",
            "variables": dict(variables)
        })

        if isinstance(statement, ast.Assign):
            value = evaluate_expression(statement.value, variables)

            for target in statement.targets:
                if not isinstance(target, ast.Name):
                    raise TeachingRuntimeError(
                        "Only simple variable assignments are supported."
                    )

                variables[target.id] = value

        elif isinstance(statement, ast.AugAssign):
            if not isinstance(statement.target, ast.Name):
                raise TeachingRuntimeError("Unsupported assignment target.")

            name = statement.target.id

            if name not in variables or type(statement.op) not in BIN_OPS:
                raise TeachingRuntimeError("Invalid variable update.")

            variables[name] = BIN_OPS[type(statement.op)](
                variables[name],
                evaluate_expression(statement.value, variables)
            )

        elif isinstance(statement, ast.Expr):

            if (
                isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "print"
            ):
                if statement.value.keywords:
                    raise TeachingRuntimeError(
                        "print() keyword arguments are not supported."
                    )

                values = [
                    evaluate_expression(arg, variables)
                    for arg in statement.value.args
                ]

                output.append(" ".join(map(str, values)))

            else:
                evaluate_expression(statement.value, variables)

        elif isinstance(statement, ast.If):

            condition = evaluate_expression(statement.test, variables)

            branch = (
                statement.body if condition
                else statement.orelse
            )

            execute_statements(
                branch, variables, output, trace, source, depth + 1
            )

        elif isinstance(statement, ast.For):

            if not isinstance(statement.target, ast.Name):
                raise TeachingRuntimeError("Invalid loop variable.")

            values = evaluate_expression(statement.iter, variables)

            if not isinstance(values, list):
                raise TeachingRuntimeError(
                    "Only for-loops using range() are supported."
                )

            for value in values:
                variables[statement.target.id] = value

                execute_statements(
                    statement.body,
                    variables,
                    output,
                    trace,
                    source,
                    depth + 1
                )

        else:
            raise TeachingRuntimeError(
                f"Unsupported statement: {type(statement).__name__}"
            )


def run_python_simulation(source):
    try:
        tree = ast.parse(source)

        variables = {}
        output = []
        trace = []

        execute_statements(
            tree.body,
            variables,
            output,
            trace,
            source
        )

        return {
            "success": True,
            "output": output,
            "variables": variables,
            "trace": trace,
            "error": None
        }

    except (
        SyntaxError,
        TeachingRuntimeError,
        ZeroDivisionError,
        TypeError,
        ValueError
    ) as error:

        return {
            "success": False,
            "output": [],
            "variables": {},
            "trace": [],
            "error": str(error)
        }


def _reset_coding_example():
    """Callback: runs before the next script run, so changing the widget key is allowed."""
    st.session_state["coding_code"] = STARTER_CODE
    st.session_state.pop("coding_result", None)


def render_coding_lab():

    st.markdown("### 💻 Live Coding Simulation")

    st.write(
        "Write and run Python code. Explore variables, conditions, "
        "loops and program execution."
    )

    if "coding_code" not in st.session_state:
        st.session_state["coding_code"] = STARTER_CODE

    code = st.text_area(
        "Python code editor",
        key="coding_code",
        height=320
    )

    col1, col2 = st.columns(2)

    with col1:
        run = st.button(
            "▶ Run code",
            type="primary",
            use_container_width=True
        )

    with col2:
        st.button(
            "↺ Reset example",
            use_container_width=True,
            on_click=_reset_coding_example
        )

    with st.expander("💡 Suggested experiments"):
        st.markdown("""
        1. Change temperature to 35.
        2. Change the threshold to 25.
        3. Change range(1, 4) to range(1, 8).
        4. Add another print() statement.
        """)

    if run:
        st.session_state["coding_result"] = run_python_simulation(code)

    result = st.session_state.get("coding_result")

    if result:

        st.divider()

        if result["success"]:

            st.success("Program executed successfully!")

            output_col, variable_col = st.columns(2)

            with output_col:
                st.markdown("#### Console output")

                if result["output"]:
                    st.code(
                        "\n".join(result["output"]),
                        language="text"
                    )
                else:
                    st.info("No output produced.")

            with variable_col:
                st.markdown("#### Final variables")
                st.json(result["variables"])

            with st.expander("🔍 Execution trace"):

                for index, step in enumerate(result["trace"], 1):

                    st.markdown(
                        f"**Step {index} — Line {step['line']}**"
                    )

                    st.code(step["code"])

                    st.json(step["variables"])

        else:
            st.error(result["error"])


# ============================================================
# IOT LABS
# ============================================================

def render_iot_labs():
    """IoT course: breadboard lab, plus the control-loop lab when available."""
    if render_iot_lab is None:
        render_breadboard_lab()
        return

    lab = st.radio(
        "Choose an IoT lab",
        ["🔌 Breadboard & circuits", "🌡️ Smart-room control loop"],
        horizontal=True,
        key="iot_lab_choice",
    )
    if lab.startswith("🔌"):
        render_breadboard_lab()
    else:
        render_iot_lab()


# ============================================================
# MAIN INTERACTIVE LAB PAGE
# ============================================================

def render_interactive_labs():

    st.subheader("Interactive Engineering Labs")

    st.write(
        "Experiment with engineering concepts through practical "
        "interactive simulations."
    )

    course = st.selectbox(
        "Choose your course",
        [
            "Computer Engineering",
            "Internet of Things (IoT)"
        ],
        key="interactive_lab_course"
    )

    if course == "Computer Engineering":
        render_coding_lab()

    elif course == "Internet of Things (IoT)":
        render_iot_labs()