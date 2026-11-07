"""Fictional demo curricula. Replace only with authorized university content."""
COURSES = {
    "Computer Engineering": {
        "topics": ["Algorithms", "Data Structures", "Pointers", "Stack and Heap", "Recursion", "Complexity", "Python"],
        "description": "Algorithms and data structures: arrays, linked lists, pointers, recursion, stack/heap memory, algorithm complexity, execution traces and debugging.",
        "oral_format": "An oral viva with 3 sequential questions. Begin with an explanation, follow with a code/stack-heap example, and finish with a counterexample or complexity trade-off. Ask one question per turn.",
        "written_format": "Three short-answer questions including algorithm reasoning, Python code tracing, and a complexity or memory diagram interpretation.",
        "rubric": "Accuracy of conceptual explanation; correct code or memory reasoning; ability to explain trade-offs. AI feedback is formative, NOT an official grade.",
        "sample_questions": [
            "Explain the difference between stack and heap memory using a linked-list example.",
            "What is the time complexity of binary search, and which prerequisite must its input satisfy?",
            "Describe how a pointer-based linked list differs from an array when inserting at the beginning.",
            "Explain recursion and identify what causes a stack overflow.",
        ],
        "mini_material": "A stack stores call frames during function execution. Heap allocation stores objects with dynamic lifetimes. A singly-linked list stores a value and reference to its next node. Binary search takes O(log n) on sorted data.",
    },
    "Internet of Things (IoT)": {
        "topics": ["Sensors", "Microcontrollers", "Breadboards", "Ohm's Law", "GPIO", "Networking", "Control Loops"],
        "description": "IoT fundamentals: sensors and actuators, Arduino and ESP32, GPIO, breadboard circuits, current limiting, communication protocols and simple control loops.",
        "oral_format": "A 3-question oral viva: describe a component, diagnose a real circuit or sensor reading, and explain a trade-off or safety issue. Ask one question at a time.",
        "written_format": "Three problems: calculate a circuit quantity, explain a sensor/control scenario, and debug a microcontroller/GPIO configuration.",
        "rubric": "Physics and electronics correctness; clear circuit reasoning; safety-aware troubleshooting; practical understanding. AI feedback is formative, NOT an official grade.",
        "sample_questions": [
            "Why does an LED need a current-limiting resistor, and how would you calculate one?",
            "Explain the difference between analogue and digital sensor outputs.",
            "What happens if a GPIO output pin is connected directly to ground while driven HIGH?",
            "How would you build a temperature-controlled fan with an ESP32?",
        ],
        "mini_material": "Ohm's law is V=IR. An LED requires a current-limiting resistor. GPIO pins can read or drive digital signals within their electrical limits. Sensor feedback can regulate an actuator in a control loop.",
    },
}


def classify_topic(question: str, course: str) -> str:
    import re
    q = question.lower()
    variants = {
        "Pointers": ["pointer", "memory address", "linked list", "reference"],
        "Stack and Heap": ["stack", "heap", "allocation"],
        "Complexity": ["complexity", "big o", "runtime", "binary search"],
        "Algorithms": ["algorithm", "sort", "search"],
        "Data Structures": ["data structure", "array", "list", "queue", "tree"],
        "Recursion": ["recursive", "recursion"],
        "Python": ["python", "for loop", "while loop", "code"],
        "Ohm's Law": ["ohm", "resistor", "current", "voltage"],
        "GPIO": ["gpio", "output pin", "input pin"],
        "Sensors": ["sensor", "temperature", "humidity"],
        "Microcontrollers": ["arduino", "esp32", "microcontroller"],
        "Breadboards": ["breadboard", "wire", "led"],
        "Networking": ["mqtt", "wifi", "network"],
        "Control Loops": ["actuator", "control loop", "feedback"],
    }
    for topic in COURSES[course]["topics"]:
        words = variants.get(topic, [topic.lower()])
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in words):
            return topic
    return "General clarification"
