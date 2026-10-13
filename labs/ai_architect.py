"""The AI Architect: four-week Python lab curriculum shown at /lab.

Lesson text comes from the May 2026 course design. Each item has:
  id, week, kind ("lesson" | "lab" | "capstone"), label, title, eyebrow,
  body (HTML paragraphs), callout, subhead, outcomes, steps, challenge,
  file (editor tab name), starter (code), solution (code or None).

Edit text here; the page reads it on every request. Keep <code> for inline
code. Starter and solution code are tested by tests/test_lab_code.py.
"""

TRICKS = '''tricks = [
    "Ollie", "Kickflip", "Heelflip", "360 Flip",
    "Kickflip", "Varial Flip", "Heelflip", "Kickflip",
    "Ollie", "Nollie", "Kickflip", "360 Flip",
    "Hardflip", "Kickflip", "Heelflip", "Varial Flip",
    "Ollie", "Kickflip", "Nollie", "Ollie",
    "Kickflip", "360 Flip", "Heelflip", "Kickflip",
    "Boardslide", "Ollie", "Nosegrind", "Kickflip",
    "Ollie", "Heelflip", "360 Flip", "Kickflip",
]'''

WEEKS = {
    1: "The probability engine",
    2: "The data engineer",
    3: "The neural layer",
    4: "The portfolio launch",
}

CURRICULUM = [
    # ───────────────────────── Week 1 ─────────────────────────
    {
        "id": "w1-l1", "week": 1, "kind": "lesson", "label": "Lesson 1",
        "title": "What is a prediction?",
        "eyebrow": "Week 1 · Lesson 1",
        "body": """<p>Before we write a single line of code, let's settle something: AI is not thinking. It's not creative. It's not magic. It's a very fast, very large prediction machine, and prediction is just math you already know.</p>
<p>In this lesson we ask one question: <em>if a skater just landed a Kickflip, what do they do next?</em> Your answer, before you look at any data, is already a probability model. You've been building bigrams in your head your whole life.</p>""",
        "callout": {"label": "The Noros principle", "text": "The computer doesn't know what a Kickflip is. It only knows numbers. Say this to yourself three times. It unlocks everything."},
        "subhead": "What you'll understand by the end",
        "outcomes": [
            {"label": "Concept", "text": "Why prediction = probability"},
            {"label": "Insight", "text": "Your intuition is already a model"},
            {"label": "Vocabulary", "text": "Bigram, token, probability"},
            {"label": "Mindset", "text": "AI is engineered, not magical"},
        ],
        "steps": None,
        "challenge": None,
        "file": "intuition.py",
        "starter": '''# Week 1 · Lesson 1 — What is a prediction?
# No data yet. Just your intuition, written as numbers.
#
# A skater just landed a Kickflip. What do they do next?
# Give each trick a chance between 0 and 1. They should add up to 1.0.

guess = {
    "Heelflip": 0.0,
    "Ollie": 0.0,
    "360 Flip": 0.0,
    "Varial Flip": 0.0,
}

total = sum(guess.values())
print("Your chances add up to", round(total, 2))

if abs(total - 1.0) > 0.01:
    print("Adjust your numbers so they add up to 1.0, then run again.")
else:
    best = max(guess, key=guess.get)
    print("After Kickflip, your model predicts:", best)
    print("Congratulations: you just built a probability model in your head.")
''',
        "solution": None,
    },
    {
        "id": "w1-l2", "week": 1, "kind": "lesson", "label": "Lesson 2",
        "title": "Build the bigram matrix",
        "eyebrow": "Week 1 · Lesson 2",
        "body": """<p>Now we write the math. A bigram matrix is a table that answers one question for every pair of items: <em>how often does B follow A?</em> We'll build it from scratch using nothing but Python dictionaries. No NumPy, no libraries, no black boxes.</p>
<p>By the end you'll have a 2D structure that holds the entire "knowledge" of your model. It'll fit on one screen and you'll be able to explain every number in it. That's the goal.</p>""",
        "callout": {"label": "Why no libraries yet?", "text": "PyTorch and NumPy are incredible tools, but using them before you understand the math underneath is like using a calculator before you understand addition. We'll get there. Not yet."},
        "subhead": "Steps",
        "outcomes": None,
        "steps": [
            "Loop through the trick list using <code>zip(tricks, tricks[1:])</code> to get consecutive pairs",
            "For each pair, increment <code>counts[current][next]</code> by 1",
            "Divide each row by its total to get probabilities. That's normalization",
            "Print your matrix and check: does every row sum to 1.0?",
        ],
        "challenge": {"label": "Think about it", "text": "What happens if a trick only ever appears once? What does the model 'know' about it? Is that a problem?"},
        "file": "bigram_matrix.py",
        "starter": "# Week 1 · Lesson 2 — Build the bigram matrix\n\n" + TRICKS + '''

# Step 1-2: count how often each trick follows each other trick
counts = {}
for current, next_trick in zip(tricks, tricks[1:]):
    pass  # YOUR CODE HERE: add 1 to counts[current][next_trick]

# Step 3: turn each row of counts into probabilities
probs = {}
# YOUR CODE HERE

# Step 4: print the matrix and check every row sums to 1.0
for trick, row in probs.items():
    print(f"{trick:<12}", {k: round(v, 2) for k, v in row.items()}, "sum =", round(sum(row.values()), 2))
''',
        "solution": "# Week 1 · Lesson 2 — SOLUTION\n\n" + TRICKS + '''

counts = {}
for current, next_trick in zip(tricks, tricks[1:]):
    if current not in counts:
        counts[current] = {}
    counts[current][next_trick] = counts[current].get(next_trick, 0) + 1

probs = {}
for trick, row in counts.items():
    total = sum(row.values())
    probs[trick] = {k: v / total for k, v in row.items()}

for trick, row in probs.items():
    print(f"{trick:<12}", {k: round(v, 2) for k, v in row.items()}, "sum =", round(sum(row.values()), 2))
''',
    },
    {
        "id": "w1-lab", "week": 1, "kind": "lab", "label": "Lab",
        "title": "Trick-list predictor",
        "eyebrow": "Week 1 · Lab",
        "body": """<p>You've seen the theory. Now you build it. Your program will read the trick dataset, construct the full probability matrix, and predict what comes next for any given trick.</p>
<p>The starter code is pre-loaded in the editor. It has <code>pass</code> placeholders, one for each step. Replace them with real code. Then hit Run.</p>""",
        "callout": {"label": "Your success metric", "text": "When you run the code and see 'After Ollie → Kickflip', you've built your first AI model. No exaggeration."},
        "subhead": "Stretch challenge",
        "outcomes": None,
        "steps": [
            "Add a <code>generate_sequence(start, n)</code> function that chains predictions together into a full trick line",
            "Change the dataset to a list of your own words and observe how the model's 'personality' changes",
            "Print a visual probability bar for each trick using just string multiplication: <code>'█' * int(prob * 20)</code>",
        ],
        "challenge": {"label": "Portfolio note", "text": "Screenshot your output. This is Week 1 of your AI portfolio. It's not impressive yet, but it's foundational. Save everything."},
        "file": "bigram_predictor.py",
        "starter": '''# Week 1 Lab — Build the Bigram Predictor
# ─────────────────────────────────────────
# Your dataset: a sequence of skateboard tricks
# Each consecutive pair is one "observation"

''' + TRICKS + '''

# ── STEP 1 ──────────────────────────────
# Build a counts dictionary.
# counts["Ollie"]["Kickflip"] = number of times
# Kickflip followed Ollie in the list above.

counts = {}

for current, next_trick in zip(tricks, tricks[1:]):
    pass  # YOUR CODE HERE


# ── STEP 2 ──────────────────────────────
# Convert counts → probabilities.
# For each starter trick, divide each count
# by the total count for that trick.

probs = {}

# YOUR CODE HERE


# ── STEP 3 ──────────────────────────────
# Write predict_next(trick).
# Return the next trick with the highest probability.

def predict_next(trick):
    pass  # YOUR CODE HERE


# ── TEST IT ─────────────────────────────
print("After Ollie, the model predicts:", predict_next("Ollie"))
print("After Kickflip, the model predicts:", predict_next("Kickflip"))
print("After Heelflip, the model predicts:", predict_next("Heelflip"))
''',
        "solution": '''# Week 1 Lab — SOLUTION
# ─────────────────────────────────────────

''' + TRICKS + '''

# STEP 1 — Count consecutive pairs
counts = {}
for current, next_trick in zip(tricks, tricks[1:]):
    if current not in counts:
        counts[current] = {}
    counts[current][next_trick] = counts[current].get(next_trick, 0) + 1

# STEP 2 — Convert to probabilities
probs = {}
for trick, following in counts.items():
    total = sum(following.values())
    probs[trick] = {k: v / total for k, v in following.items()}

# STEP 3 — Predict most likely next trick
def predict_next(trick):
    if trick not in probs:
        return "Unknown trick"
    return max(probs[trick], key=probs[trick].get)

# STRETCH — Generate a sequence
def generate_sequence(start, n=5):
    sequence = [start]
    current = start
    for _ in range(n - 1):
        nxt = predict_next(current)
        if nxt == "Unknown trick":
            break
        sequence.append(nxt)
        current = nxt
    return " → ".join(sequence)

# Test it
print("After Ollie    →", predict_next("Ollie"))
print("After Kickflip →", predict_next("Kickflip"))
print("After Heelflip →", predict_next("Heelflip"))
print()
print("Generated sequence:")
print(generate_sequence("Ollie", 6))
print()
print("The bigram probabilities for 'Ollie':")
for trick, prob in sorted(probs.get("Ollie", {}).items(), key=lambda x: -x[1]):
    bar = "█" * int(prob * 20)
    print(f"  {trick:<15} {bar} {prob:.0%}")
''',
    },

    # ───────────────────────── Week 2 ─────────────────────────
    {
        "id": "w2-l3", "week": 2, "kind": "lesson", "label": "Lesson 3",
        "title": "Data shape = model personality",
        "eyebrow": "Week 2 · Lesson 3",
        "body": """<p>Here's the most important thing you'll learn in this entire course: <em>the model is only as good as its data.</em> Change the data, you change the model. Use sloppy data, you get sloppy predictions. Use rich, structured data, you get a model that actually behaves intelligently.</p>
<p>This week we move from a curated trick list to raw, messy input: typos, inconsistent capitalization, duplicate entries, and missing values. Welcome to real-world data engineering.</p>""",
        "callout": {"label": "The garbage-in principle", "text": "A lot of the AI failures you've seen, like a chatbot giving weird advice or an autocomplete going off the rails, trace back to data that wasn't cleaned or checked properly."},
        "subhead": "What you'll understand by the end",
        "outcomes": [
            {"label": "Concept", "text": "Why data cleaning matters"},
            {"label": "Skill", "text": "Normalize, deduplicate, validate"},
            {"label": "Insight", "text": "Data is the AI's worldview"},
            {"label": "Vocabulary", "text": "Corpus, normalization, token"},
        ],
        "steps": None,
        "challenge": None,
        "file": "clean_data.py",
        "starter": '''# Week 2 · Lesson 3 — Data shape = model personality
# Real data is messy. Same trick, five different spellings:

raw = ["Kickflip", "kickflip ", "KICKFLIP!", "Ollie", " ollie", "",
       "Heelflip", "heelflip?", None, "360 Flip", "360 flip"]

def clean(item):
    """Return a tidy version of one entry, or None if it's unusable."""
    # YOUR CODE HERE: skip empty/missing values, lowercase,
    # strip spaces, and remove punctuation like ! and ?
    return item

cleaned = [clean(x) for x in raw]
print("Before:", raw)
print("After: ", cleaned)
print("Unique tricks before:", len(set(raw)))
print("Unique tricks after: ", len({x for x in cleaned if x}))
''',
        "solution": '''# Week 2 · Lesson 3 — SOLUTION

raw = ["Kickflip", "kickflip ", "KICKFLIP!", "Ollie", " ollie", "",
       "Heelflip", "heelflip?", None, "360 Flip", "360 flip"]

def clean(item):
    """Return a tidy version of one entry, or None if it's unusable."""
    if not item or not item.strip():
        return None
    text = item.lower().strip()
    text = "".join(ch for ch in text if ch.isalnum() or ch == " ")
    return " ".join(text.split())  # collapse extra spaces

cleaned = [clean(x) for x in raw]
print("Before:", raw)
print("After: ", cleaned)
print("Unique tricks before:", len(set(raw)))
print("Unique tricks after: ", len({x for x in cleaned if x}))
''',
    },
    {
        "id": "w2-l4", "week": 2, "kind": "lesson", "label": "Lesson 4",
        "title": "Tensors without the terror",
        "eyebrow": "Week 2 · Lesson 4",
        "body": """<p>A tensor is just an array of arrays. That's it. The word sounds intimidating because the ML world wraps it in jargon, but you built a 2D tensor last week. It was your bigram matrix.</p>
<p>In this lesson we go one dimension deeper. Instead of counting pairs of words, we'll count triplets, and discover that the more context we give the model, the smarter its predictions become. We'll also meet NumPy for the first time, now that you understand what it's doing under the hood.</p>""",
        "callout": {"label": "The key insight", "text": "A 1D tensor is a list. A 2D tensor is a table. A 3D tensor is a stack of tables. Every neural network, including the ones behind ChatGPT, is doing math on tensors."},
        "subhead": "Steps",
        "outcomes": None,
        "steps": [
            "Convert your trick list to integer indices: each unique trick gets a number",
            "Build a 2D NumPy array using those indices instead of strings",
            "Compare your Week 1 dictionary approach to the NumPy approach: same result, different speed",
            "Experiment: what does a 3-gram (triplet) matrix look like? Build one.",
        ],
        "challenge": {"label": "Stretch", "text": "How many cells does a trigram matrix have if you have 50 unique tricks? How about 5,000 unique words? What does this tell you about why LLMs are expensive to train?"},
        "file": "tensors.py",
        "starter": "# Week 2 · Lesson 4 — Tensors without the terror\n# (The first run takes a few seconds while NumPy loads.)\nimport numpy as np\n\n" + TRICKS + '''

# Step 1: give each unique trick a number
vocab = sorted(set(tricks))
index = {trick: i for i, trick in enumerate(vocab)}
print("Vocabulary:", index)

# Step 2: a 2D tensor of counts, shape (vocab size, vocab size)
counts = np.zeros((len(vocab), len(vocab)), dtype=int)
for a, b in zip(tricks, tricks[1:]):
    pass  # YOUR CODE HERE: add 1 to counts[index[a], index[b]]

print(counts)
print("Shape:", counts.shape)

# Step 4: a 3D tensor for triplets would have shape (V, V, V).
# YOUR CODE HERE
''',
        "solution": "# Week 2 · Lesson 4 — SOLUTION\nimport numpy as np\n\n" + TRICKS + '''

vocab = sorted(set(tricks))
index = {trick: i for i, trick in enumerate(vocab)}
print("Vocabulary:", index)

counts = np.zeros((len(vocab), len(vocab)), dtype=int)
for a, b in zip(tricks, tricks[1:]):
    counts[index[a], index[b]] += 1
print(counts)
print("Shape:", counts.shape)

# Turn counts into probabilities, row by row
row_totals = counts.sum(axis=1, keepdims=True)
probs = np.divide(counts, row_totals, out=np.zeros(counts.shape), where=row_totals > 0)
print("After Ollie →", vocab[probs[index["Ollie"]].argmax()])

# Triplets: a stack of tables
tri = np.zeros((len(vocab),) * 3, dtype=int)
for a, b, c in zip(tricks, tricks[1:], tricks[2:]):
    tri[index[a], index[b], index[c]] += 1
print("Trigram shape:", tri.shape, "→", tri.size, "cells")
print("With 5,000 words:", 5000 ** 3, "cells")
''',
    },
    {
        "id": "w2-lab", "week": 2, "kind": "lab", "label": "Lab",
        "title": "Custom dataset challenge",
        "eyebrow": "Week 2 · Lab",
        "body": """<p>This lab has a twist: you bring your own data. The starter code loads a sample list, but your job is to swap it out for something personal. Song titles. Your favorite movies. Pokémon names. Whatever you care about.</p>
<p>Then you'll clean it (lowercase everything, strip punctuation, remove empty entries) and build a bigram model on it. At the end, your model will feel uniquely yours, because it is.</p>""",
        "callout": {"label": "Why this matters", "text": "Phone keyboards' next-word suggestions started out as exactly this kind of n-gram model, trained on huge amounts of text. Today's systems are bigger, but the core idea, learn patterns from data, is the one you're building."},
        "subhead": "Requirements",
        "outcomes": None,
        "steps": [
            "Choose a dataset of at least 30 items (the more the better)",
            "Write a <code>clean(text)</code> function that normalizes your data",
            "Build the bigram matrix on your cleaned data",
            "Generate 5 sequences and evaluate: do they feel 'right' for your dataset?",
        ],
        "challenge": {"label": "Portfolio note", "text": "Name your dataset something memorable. 'MyModel trained on Taylor Swift song titles' is a far more compelling portfolio entry than 'bigram_v2.py'."},
        "file": "my_model.py",
        "starter": '''# Week 2 Lab — Custom dataset challenge
import random

# Replace this with at least 30 items of your own, in order.
my_data = """
the cat sat on the mat. the dog sat on the log.
the cat saw the dog. the dog saw the cat sat on the log!
""".split()

def clean(text):
    # YOUR CODE HERE: lowercase, strip punctuation, return None if empty
    return text

words = [w for w in (clean(x) for x in my_data) if w]
print(len(words), "items after cleaning")

# YOUR CODE HERE: build counts and probabilities (like Week 1)
probs = {}

def generate(start, n=8):
    out = [start]
    for _ in range(n - 1):
        options = probs.get(out[-1])
        if not options:
            break
        out.append(random.choices(list(options), weights=list(options.values()))[0])
    return " ".join(out)

for _ in range(5):
    print(generate(words[0]))
''',
        "solution": '''# Week 2 Lab — SOLUTION (with the sample data)
import random

my_data = """
the cat sat on the mat. the dog sat on the log.
the cat saw the dog. the dog saw the cat sat on the log!
""".split()

def clean(text):
    text = "".join(ch for ch in text.lower() if ch.isalnum())
    return text or None

words = [w for w in (clean(x) for x in my_data) if w]
print(len(words), "items after cleaning")

counts = {}
for a, b in zip(words, words[1:]):
    counts.setdefault(a, {})
    counts[a][b] = counts[a].get(b, 0) + 1
probs = {a: {b: c / sum(row.values()) for b, c in row.items()} for a, row in counts.items()}

def generate(start, n=8):
    out = [start]
    for _ in range(n - 1):
        options = probs.get(out[-1])
        if not options:
            break
        out.append(random.choices(list(options), weights=list(options.values()))[0])
    return " ".join(out)

for _ in range(5):
    print(generate(words[0]))
''',
    },

    # ───────────────────────── Week 3 ─────────────────────────
    {
        "id": "w3-l5", "week": 3, "kind": "lesson", "label": "Lesson 5",
        "title": "One neuron from scratch",
        "eyebrow": "Week 3 · Lesson 5",
        "body": """<p>This is the week everything changes. We're going to stop counting and start <em>learning</em>. The difference: a bigram model just remembers what it's seen. A neural network adjusts its own weights based on what it gets wrong.</p>
<p>We start with exactly one neuron. One input, one weight, one output, one bias. It's laughably simple. But by the end of this lesson you'll understand the core mechanism behind every neural network that has ever existed.</p>""",
        "callout": {"label": "The aha moment", "text": "A neuron is just: output = (input × weight) + bias. That's the whole thing. The 'learning' is just adjusting weight and bias until the output is right."},
        "subhead": "What you'll understand by the end",
        "outcomes": [
            {"label": "Concept", "text": "Weights, bias, activation"},
            {"label": "Skill", "text": "Forward pass by hand"},
            {"label": "Insight", "text": "Learning = adjusting numbers"},
            {"label": "Vocabulary", "text": "Neuron, weight, bias, sigmoid"},
        ],
        "steps": None,
        "challenge": None,
        "file": "neuron.py",
        "starter": '''# Week 3 · Lesson 5 — One neuron from scratch
import math

def sigmoid(z):
    """Squashes any number into the range 0 to 1."""
    return 1 / (1 + math.exp(-z))

def neuron(x, weight, bias):
    # YOUR CODE HERE: return sigmoid of (x * weight + bias)
    pass

# Try it: change weight and bias and watch the output move
for x in [0, 1, 2, 3]:
    print("input", x, "→ output", neuron(x, weight=0.5, bias=-1.0))
''',
        "solution": '''# Week 3 · Lesson 5 — SOLUTION
import math

def sigmoid(z):
    return 1 / (1 + math.exp(-z))

def neuron(x, weight, bias):
    return sigmoid(x * weight + bias)

for x in [0, 1, 2, 3]:
    print("input", x, "→ output", round(neuron(x, weight=0.5, bias=-1.0), 3))
''',
    },
    {
        "id": "w3-l6", "week": 3, "kind": "lesson", "label": "Lesson 6",
        "title": "Loss functions and learning",
        "eyebrow": "Week 3 · Lesson 6",
        "body": """<p>How does a neural network know when it's wrong? It uses a loss function: a single number that measures how far off the prediction is. The goal of training is to make that number as small as possible.</p>
<p>We'll implement squared error from scratch, then watch our tiny network's loss shrink as we adjust its weight step by step. This is gradient descent, stripped completely bare. No calculus required to understand the intuition.</p>""",
        "callout": {"label": "The mountain metaphor", "text": "Imagine standing on a foggy mountain, trying to find the lowest valley. You can't see far, so you take a small step downhill, check your altitude, and repeat. That's gradient descent, and it's how today's language models are trained."},
        "subhead": "Steps",
        "outcomes": None,
        "steps": [
            "Implement squared-error loss: <code>loss = (prediction - target) ** 2</code>",
            "Manually nudge the weight up and down and watch the loss change",
            "Write a loop that takes 100 tiny steps in the direction that reduces loss",
            "Plot the loss curve using a simple print-based sparkline",
        ],
        "challenge": {"label": "Think about it", "text": "What happens if your step size (learning rate) is too large? What if it's too small? Try both and describe what you observe."},
        "file": "gradient_descent.py",
        "starter": '''# Week 3 · Lesson 6 — Loss functions and learning
x, target = 2.0, 0.8     # we want the neuron to output 0.8 for input 2
weight = 0.0
learning_rate = 0.01

def predict(w):
    return x * w

def loss(w):
    # YOUR CODE HERE: squared error between predict(w) and target
    return 0.0

history = [loss(weight)]
for step in range(100):
    # Which way is downhill? Peek a tiny bit to each side.
    nudge = 0.001
    slope = (loss(weight + nudge) - loss(weight - nudge)) / (2 * nudge)
    # YOUR CODE HERE: move weight a small step downhill
    history.append(loss(weight))

print("final weight:", round(weight, 4), " prediction:", round(predict(weight), 4))
bars = " ▁▂▃▄▅▆▇█"
top = max(history) or 1
print("loss curve:", "".join(bars[min(8, int(h / top * 8))] for h in history[::4]))
''',
        "solution": '''# Week 3 · Lesson 6 — SOLUTION
x, target = 2.0, 0.8
weight = 0.0
learning_rate = 0.01

def predict(w):
    return x * w

def loss(w):
    return (predict(w) - target) ** 2

history = [loss(weight)]
for step in range(100):
    nudge = 0.001
    slope = (loss(weight + nudge) - loss(weight - nudge)) / (2 * nudge)
    weight -= learning_rate * slope
    history.append(loss(weight))

print("final weight:", round(weight, 4), " prediction:", round(predict(weight), 4))
bars = " ▁▂▃▄▅▆▇█"
top = max(history) or 1
print("loss curve:", "".join(bars[min(8, int(h / top * 8))] for h in history[::4]))
''',
    },
    {
        "id": "w3-lab", "week": 3, "kind": "lab", "label": "Lab",
        "title": "Train a mini-network",
        "eyebrow": "Week 3 · Lab",
        "body": """<p>You've built one neuron. Now we stack them. This is a minimal two-layer network, input → hidden → output, trained on your trick dataset to predict the next trick in a sequence.</p>
<p>It won't outperform the bigram model. That's intentional. The point is to see that the neural network approach and the probability approach are different ways of doing the same job, and to understand why the neural approach scales better when the dataset gets huge.</p>""",
        "callout": {"label": "Why this matters", "text": "GPT-3 has 175 billion parameters (weights). Your network has a few hundred. The building blocks are the same: weights, sums, and gradient descent, at a very different scale."},
        "subhead": "What to build",
        "outcomes": None,
        "steps": [
            "Encode your tricks as one-hot vectors (a list with a 1 in one position, 0s everywhere else)",
            "Build a two-layer network: input → hidden → output",
            "Train it for 500 steps using gradient descent, like Lesson 6",
            "Compare its predictions to your Week 1 bigram model: where do they agree? Where do they differ?",
        ],
        "challenge": {"label": "Portfolio note", "text": "This is the most impressive thing in your portfolio so far. A trained neural network, even a tiny one, is something most adults have never built. Document what you made."},
        "file": "mini_network.py",
        "starter": "# Week 3 Lab — Train a mini-network\n# Pure Python, no libraries. Fill in the two YOUR CODE HERE spots.\nimport math, random\nrandom.seed(1)\n\n" + TRICKS + '''

vocab = sorted(set(tricks))
V, H = len(vocab), 8                      # vocab size, hidden size
idx = {t: i for i, t in enumerate(vocab)}
pairs = [(idx[a], idx[b]) for a, b in zip(tricks, tricks[1:])]

# Weights: input→hidden (V x H) and hidden→output (H x V)
W1 = [[random.uniform(-0.5, 0.5) for _ in range(H)] for _ in range(V)]
W2 = [[random.uniform(-0.5, 0.5) for _ in range(V)] for _ in range(H)]

def softmax(zs):
    m = max(zs)
    exps = [math.exp(z - m) for z in zs]
    s = sum(exps)
    return [e / s for e in exps]

def forward(i):
    # One-hot input means the hidden layer is just row i of W1
    hidden = [math.tanh(w) for w in W1[i]]
    # YOUR CODE HERE: output scores = hidden · W2, then softmax
    scores = [0.0] * V
    return hidden, softmax(scores)

lr = 0.1
for step in range(500):
    i, target = random.choice(pairs)
    hidden, probs = forward(i)
    # Gradient of the loss with respect to each output score
    d_out = [p - (1 if k == target else 0) for k, p in enumerate(probs)]
    # Backpropagate into the hidden layer, then update both weight tables
    d_hidden = [sum(d_out[k] * W2[h][k] for k in range(V)) * (1 - hidden[h] ** 2) for h in range(H)]
    # YOUR CODE HERE: W2[h][k] -= lr * hidden[h] * d_out[k]  (for every h, k)
    for h in range(H):
        W1[i][h] -= lr * d_hidden[h]

for t in ["Ollie", "Kickflip", "Heelflip"]:
    _, probs = forward(idx[t])
    print(f"After {t:<9} → network says {vocab[probs.index(max(probs))]}")
''',
        "solution": "# Week 3 Lab — SOLUTION\nimport math, random\nrandom.seed(1)\n\n" + TRICKS + '''

vocab = sorted(set(tricks))
V, H = len(vocab), 8
idx = {t: i for i, t in enumerate(vocab)}
pairs = [(idx[a], idx[b]) for a, b in zip(tricks, tricks[1:])]

W1 = [[random.uniform(-0.5, 0.5) for _ in range(H)] for _ in range(V)]
W2 = [[random.uniform(-0.5, 0.5) for _ in range(V)] for _ in range(H)]

def softmax(zs):
    m = max(zs)
    exps = [math.exp(z - m) for z in zs]
    s = sum(exps)
    return [e / s for e in exps]

def forward(i):
    hidden = [math.tanh(w) for w in W1[i]]
    scores = [sum(hidden[h] * W2[h][k] for h in range(H)) for k in range(V)]
    return hidden, softmax(scores)

lr = 0.1
for step in range(500):
    i, target = random.choice(pairs)
    hidden, probs = forward(i)
    d_out = [p - (1 if k == target else 0) for k, p in enumerate(probs)]
    d_hidden = [sum(d_out[k] * W2[h][k] for k in range(V)) * (1 - hidden[h] ** 2) for h in range(H)]
    for h in range(H):
        for k in range(V):
            W2[h][k] -= lr * hidden[h] * d_out[k]
    for h in range(H):
        W1[i][h] -= lr * d_hidden[h]

for t in ["Ollie", "Kickflip", "Heelflip"]:
    _, probs = forward(idx[t])
    print(f"After {t:<9} → network says {vocab[probs.index(max(probs))]}  ({max(probs):.0%} sure)")
''',
    },

    # ───────────────────────── Week 4 ─────────────────────────
    {
        "id": "w4-l7", "week": 4, "kind": "lesson", "label": "Lesson 7",
        "title": "From script to app",
        "eyebrow": "Week 4 · Lesson 7",
        "body": """<p>Everything you've built so far lives in a terminal. That's fine for learning, but a portfolio project needs to be <em>showable</em>. In this lesson we plan how to wrap your model in a simple web app with Streamlit.</p>
<p>Streamlit is a Python library that turns scripts into web apps with very little extra code. It's the fastest path from "working model" to "thing I can show my parents and college admissions officers." Streamlit runs on a computer, not inside this browser lab, so here we practice the most important habit first: keeping the model separate from the screen that shows it.</p>""",
        "callout": {"label": "What you're building toward", "text": "By the end of Week 4, you will have a running AI app that you built from scratch. No templates, no drag-and-drop. Yours."},
        "subhead": "What you'll understand by the end",
        "outcomes": [
            {"label": "Skill", "text": "Streamlit layout and widgets"},
            {"label": "Concept", "text": "Separating model from UI"},
            {"label": "Output", "text": "A runnable app file"},
            {"label": "Vocabulary", "text": "st.write, st.slider, st.button"},
        ],
        "steps": None,
        "challenge": None,
        "file": "app_plan.py",
        "starter": '''# Week 4 · Lesson 7 — From script to app
# The model: knows nothing about screens.
probs = {
    "ollie": {"kickflip": 0.5, "nollie": 0.17, "heelflip": 0.17, "nosegrind": 0.16},
    "kickflip": {"heelflip": 0.4, "360 flip": 0.2, "ollie": 0.2, "varial flip": 0.1, "nollie": 0.1},
}

def predict_next(word):
    options = probs.get(word.lower())
    return max(options, key=options.get) if options else None

# The "screen": in Streamlit these lines become st.title, st.text_input
# and st.write. Here we fake the screen with print().
def show_app(user_input):
    print("=== My Trick Predictor ===")
    print("You typed:", user_input)
    guess = predict_next(user_input)
    # YOUR CODE HERE: print a friendly message, and handle guess being None

show_app("Ollie")
show_app("Boardslide")

# On your own computer, the Streamlit version looks like:
#   import streamlit as st
#   st.title("My Trick Predictor")
#   word = st.text_input("Last trick")
#   if word: st.write("Next up:", predict_next(word))
''',
        "solution": None,
    },
    {
        "id": "w4-l8", "week": 4, "kind": "lesson", "label": "Lesson 8",
        "title": "Design for a human",
        "eyebrow": "Week 4 · Lesson 8",
        "body": """<p>Your app works. Now make it make sense to someone who didn't build it. This lesson is about the one skill most CS courses skip entirely: <em>explaining your work to a non-technical audience.</em></p>
<p>We'll add a plain-English explanation, a visual probability bar, and an "about this model" section that describes what your AI does and doesn't know. This is the difference between a school project and a portfolio piece.</p>""",
        "callout": {"label": "The Noros standard", "text": "Human-centered AI means your app should be usable by your grandmother and impressive to a computer science professor. Both at once. That's the bar."},
        "subhead": "What to add",
        "outcomes": None,
        "steps": [
            "A plain-English intro: 'This model was trained on X items and learned Y patterns'",
            "A probability bar showing the top 5 predictions and their confidence",
            "An 'under the hood' section that shows the raw bigram matrix for curious users",
            "Your name, the course name, and the week, because attribution matters",
        ],
        "challenge": {"label": "Optional add-on", "text": "Want a public link? A bonus lesson walks you through hosting a Streamlit app on Streamlit Community Cloud."},
        "file": "explain.py",
        "starter": "# Week 4 · Lesson 8 — Design for a human\n\n" + TRICKS + '''

counts = {}
for a, b in zip(tricks, tricks[1:]):
    counts.setdefault(a, {})
    counts[a][b] = counts[a].get(b, 0) + 1

def explain(trick):
    row = counts.get(trick, {})
    total = sum(row.values())
    # YOUR CODE HERE:
    # 1. A plain-English sentence about what the model learned
    # 2. The top 5 next tricks with a bar like "█" * int(share * 20)
    # 3. What the model can't do (e.g. tricks it has never seen)
    print(row, total)

explain("Ollie")
print("Built by: YOUR NAME · The AI Architect · Week 4")
''',
        "solution": "# Week 4 · Lesson 8 — SOLUTION\n\n" + TRICKS + '''

counts = {}
for a, b in zip(tricks, tricks[1:]):
    counts.setdefault(a, {})
    counts[a][b] = counts[a].get(b, 0) + 1

def explain(trick):
    row = counts.get(trick, {})
    total = sum(row.values())
    print(f"This model learned from {len(tricks)} tricks in a row.")
    if not total:
        print(f"It has never seen anything follow '{trick}', so it can't guess. That's its blind spot.")
        return
    print(f"It has seen '{trick}' followed by another trick {total} times. Its best guesses:")
    for nxt, c in sorted(row.items(), key=lambda kv: -kv[1])[:5]:
        share = c / total
        print(f"  {nxt:<12} {'█' * int(share * 20):<20} {share:.0%}")
    print("It only knows the trick right before. It has no idea about style, stance or skill.")

explain("Ollie")
print()
explain("Boardslide")
print()
print("Built by: YOUR NAME · The AI Architect · Week 4")
''',
    },
    {
        "id": "w4-capstone", "week": 4, "kind": "capstone", "label": "Capstone",
        "title": "Live demo + certificate",
        "eyebrow": "Week 4 · Capstone",
        "body": """<p>This is it. Your finished app, your recorded demo, your certificate. The capstone has three deliverables and they're all straightforward. The hard work is already done.</p>
<p>You'll submit your app file and record a 2-minute screen-share walkthrough where you explain what your model does, how it was trained, and what it gets right and wrong. That self-reflection is the most important part.</p>""",
        "callout": {"label": "What makes a great demo", "text": "Show it breaking. The best engineers know their tool's limits. Tell us: what kind of input confuses your model and why? That answer proves you understand what you built."},
        "subhead": "Three deliverables",
        "outcomes": None,
        "steps": [
            "<strong>The app:</strong> your finished model and app file",
            "<strong>The demo:</strong> a 2-minute screen recording explaining your model to a non-technical audience",
            "<strong>The reflection:</strong> 3–5 sentences answering: what would you need to do to make this model smarter?",
        ],
        "challenge": {"label": "Your certificate", "text": "On submission, you'll receive your Ascent Scholars certificate, signed by Dr. Jami Saffioti and ready for your college application or resume."},
        "file": "reflection.py",
        "starter": '''# Week 4 · Capstone — Live demo + certificate
# Use this space to draft your reflection, then run it to check length.

reflection = """
Write 3-5 sentences: what would you need to do to make your model smarter?
"""

sentences = [s for s in reflection.replace("!", ".").replace("?", ".").split(".") if s.strip()]
print(f"{len(sentences)} sentences")
if 3 <= len(sentences) <= 5:
    print("Good length. Now record your 2-minute demo, and show it breaking!")
else:
    print("Aim for 3 to 5 sentences.")
''',
        "solution": None,
    },
]


def curriculum_for_page():
    """Everything the lab page needs, as plain data."""
    return {"weeks": WEEKS, "items": CURRICULUM}
