import json

science_facts = [
    # Biology / Anatomy
    "DNA contains the biological instructions that make each species unique.",
    "Mitochondria generate most of the chemical energy needed to power the cell.",
    "The human brain contains about eighty-six billion neurons.",
    "Photosynthesis allows plants to convert sunlight, water, and carbon dioxide into oxygen and energy.",
    "Charles Darwin proposed the theory of evolution by natural selection.",
    "Human blood is red because it contains iron-rich hemoglobin.",
    "A single strand of DNA is thousands of times thinner than a human hair.",
    "Antibiotics only treat bacterial infections, not viral infections like the common cold.",
    "Red blood cells are the only cells in the human body that do not have a nucleus.",
    "The human skeleton is completely replaced every ten years through cellular regeneration.",
    "Vampire bats have a special protein in their saliva that stops blood from clotting.",
    "Sharks do not have any bones; their skeletons are made entirely of cartilage.",
    "Bananas share about fifty percent of their DNA with humans.",
    "Corals are not plants; they are actually marine invertebrates.",
    "The human eye can distinguish about ten million different colors.",
    "Octopuses have three hearts and blue blood.",
    "Bacteria are single-celled organisms that can be found almost everywhere on Earth.",
    "Fungi are genetically more closely related to animals than they are to plants.",
    "The human skin is the largest organ of the body.",
    "Viruses cannot reproduce on their own; they must infect a host cell.",

    # Physics / Chemistry
    "Water is the only common substance that exists naturally in all three common states of matter.",
    "Gravity causes objects to accelerate toward the center of the Earth at 9.8 meters per second squared.",
    "The speed of light in a vacuum is approximately 299,792 kilometers per second.",
    "An atom is mostly empty space, with a tiny, dense nucleus at its center.",
    "Energy cannot be created or destroyed, only transformed from one form to another.",
    "Helium is the second most abundant element in the universe, after hydrogen.",
    "Absolute zero is the theoretical temperature where all atomic movement stops.",
    "Sound travels about four times faster in water than it does in air.",
    "Diamonds and pencil lead are both made entirely of the element carbon.",
    "A neutron star is so dense that a single teaspoon of its material weighs a billion tons.",
    "Electrons have a negative charge and orbit the nucleus of an atom.",
    "The periodic table organizes chemical elements based on their atomic number.",
    "Friction is the force that resists the relative motion of solid surfaces sliding against each other.",
    "Nuclear fusion is the process that powers the sun and other stars.",
    "Kinetic energy is the energy of motion, while potential energy is stored energy.",
    "Magnetism is created by the motion of electric charges.",
    "Glass is an amorphous solid, meaning its atomic structure lacks a defined order.",
    "Ozone is a gas composed of three oxygen atoms and helps block ultraviolet radiation.",
    "Acids have a pH less than 7, while bases have a pH greater than 7.",
    "A photon is a fundamental particle of light that carries electromagnetic force.",

    # Astronomy / Earth Science
    "The universe is estimated to be about 13.8 billion years old.",
    "Earth is the only planet in our solar system not named after a Greek or Roman deity.",
    "Jupiter is so large that all the other planets in the solar system could fit inside it.",
    "The Great Red Spot on Jupiter is a giant storm that has been raging for hundreds of years.",
    "Saturn has rings made mostly of chunks of ice and rock.",
    "Venus is the hottest planet in our solar system because of its thick atmosphere.",
    "A light-year is the distance that light travels in one Earth year.",
    "Earth's tectonic plates move at about the same speed that human fingernails grow.",
    "The Marianas Trench is the deepest oceanic trench on Earth.",
    "The core of the Earth is as hot as the surface of the sun.",
    "Mars appears red because its surface is covered in iron oxide, also known as rust.",
    "There are more stars in the universe than there are grains of sand on all of Earth's beaches.",
    "A black hole has gravity so strong that not even light can escape it.",
    "The moon controls the ocean tides on Earth due to its gravitational pull.",
    "Earth's atmosphere is composed mostly of nitrogen and oxygen.",
    "Pangea was a supercontinent that existed hundreds of millions of years ago.",
    "Volcanoes form when magma from within the Earth's upper mantle works its way to the surface.",
    "An earthquake is caused by a sudden slip on a geological fault.",
    "The Milky Way is a barred spiral galaxy that contains our solar system.",
    "Pluto was reclassified as a dwarf planet in 2006 by the International Astronomical Union.",
]

technology_facts = [
    # Computing / Software
    "The first computer bug was an actual moth found trapped in a Harvard Mark II computer.",
    "The Internet is a global network of computers, while the World Wide Web is just one service on it.",
    "A single gigabyte contains one thousand megabytes of data.",
    "Binary code uses only the numbers zero and one to represent all computer data.",
    "The first computer mouse was invented in 1964 and was made out of wood.",
    "Alan Turing is widely considered to be the father of theoretical computer science.",
    "An algorithm is a step-by-step set of instructions used to solve a specific problem.",
    "Open-source software allows anyone to inspect, modify, and enhance the source code.",
    "A pixel is the smallest unit of a digital image that can be displayed on a screen.",
    "RAM stands for Random Access Memory and is used as short-term memory by a computer.",
    "The first domain name ever registered was symbolics.com in 1985.",
    "Cloud computing allows users to access data and programs over the internet instead of a local drive.",
    "Encryption is the process of converting data into a secure format to prevent unauthorized access.",
    "A motherboard is the main printed circuit board that connects all computer components.",
    "The CPU is the central processing unit, often called the brain of the computer.",
    "Phishing is a cyber attack where scammers try to trick users into revealing sensitive information.",
    "A firewall is a network security system that monitors and controls incoming and outgoing traffic.",
    "Machine learning is a branch of artificial intelligence where systems learn from data.",
    "An operating system manages computer hardware and provides common services for computer programs.",
    "The QWERTY keyboard layout was originally designed to prevent mechanical typewriters from jamming.",

    # Engineering / Inventions
    "The concept of the laser stands for light amplification by stimulated emission of radiation.",
    "Fiber optic cables transmit data using pulses of light traveling through glass threads.",
    "The global positioning system uses a network of satellites to provide location data.",
    "The first artificial Earth satellite, Sputnik 1, was launched by the Soviet Union in 1957.",
    "Batteries convert stored chemical energy into electrical energy.",
    "A semiconductor is a material with electrical conductivity between a conductor and an insulator.",
    "3D printing creates three-dimensional objects by adding material layer by layer.",
    "The microwave oven was invented accidentally by a radar engineer working with magnetrons.",
    "LED stands for light-emitting diode, a highly efficient light source.",
    "Wi-Fi uses radio waves to provide wireless high-speed internet and network connections.",
    "The Apollo 11 spacecraft that landed on the moon had less computing power than a modern smartphone.",
    "A transistor is a tiny semiconductor device used to amplify or switch electrical signals.",
    "Robotics is an interdisciplinary branch of engineering and science that deals with the design of robots.",
    "The internal combustion engine generates power by burning fuel inside a chamber.",
    "Electric vehicles use electric motors powered by rechargeable battery packs.",
    "A drone is an unmanned aerial vehicle that can be controlled remotely or fly autonomously.",
    "The first commercial mobile phone was released by Motorola in 1983.",
    "A barcode is a method of representing data in a visual, machine-readable form.",
    "Virtual reality creates a simulated environment that can be similar to or completely different from the real world.",
    "Nanotechnology is the manipulation of matter on an atomic, molecular, and supramolecular scale.",
]

everyday_facts = [
    # Geography / History
    "Mount Everest is the highest mountain on Earth above sea level.",
    "The Sahara is the largest hot desert in the world, spanning much of North Africa.",
    "The Nile River is widely considered to be the longest river in the world.",
    "The Great Wall of China is a series of ancient fortifications built along the historical northern borders of China.",
    "Antarctica is the coldest, driest, and windiest continent on Earth.",
    "The Pacific Ocean is the largest and deepest of Earth's oceanic divisions.",
    "The printing press was invented by Johannes Gutenberg in the 15th century.",
    "The Roman Empire was one of the largest and most powerful empires in human history.",
    "The Industrial Revolution marked a major turning point in history with the transition to new manufacturing processes.",
    "The United Nations was established in 1945 to promote international peace and cooperation.",

    # Language / Arts
    "William Shakespeare is widely regarded as the greatest writer in the English language.",
    "The Mona Lisa is a famous portrait painting created by the Italian artist Leonardo da Vinci.",
    "Music is an art form that uses sound and silence organized in time.",
    "Architecture is both the process and the product of planning, designing, and constructing buildings.",
    "Photography is the art and science of capturing light to create images.",
    
    # Food / Nutrition
    "Water makes up about sixty percent of the adult human body.",
    "Tomatoes are botanically classified as fruits, even though they are used as vegetables in cooking.",
    "Honey never spoils; archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old.",
    "Proteins are essential macronutrients made up of amino acids that help build and repair tissues.",
    "Vitamins and minerals are crucial for a healthy immune system and normal cell function.",
]

nature_facts = [
    # Ecosystems & Natural World
    "The Amazon Rainforest produces over twenty percent of the world's oxygen supply.",
    "A coral reef is a diverse underwater ecosystem held together by calcium carbonate structures.",
    "Photosynthesis is the foundation of almost all food webs on our planet.",
    "A tsunami is a series of massive ocean waves caused by underwater earthquakes or volcanic eruptions.",
    "Tornadoes are violently rotating columns of air that extend from a thunderstorm to the ground.",
    "The northern lights, or aurora borealis, are caused by solar wind interacting with Earth's magnetic field.",
    "Bamboo is actually a type of grass, and some species can grow up to three feet in a single day.",
    "A desert is defined by its low precipitation, not by its temperature.",
    "Glaciers are large, persistent bodies of ice that move slowly over land.",
    "Mangrove forests protect coastlines from erosion and provide vital habitats for marine life.",
]

with open('app/data/science_sentences.py', 'w') as f:
    f.write('"""Educational sentences for Science and Technology categories."""\n\n')
    f.write('SCIENCE_SENTENCES: tuple[str, ...] = (\n')
    for s in science_facts:
        f.write(f'    {repr(s)},\n')
    f.write(')\n\n')
    
    f.write('TECHNOLOGY_SENTENCES: tuple[str, ...] = (\n')
    for s in technology_facts:
        f.write(f'    {repr(s)},\n')
    f.write(')\n')

with open('app/data/general_knowledge.py', 'w') as f:
    f.write('"""Advanced factual learning sentences for everyday categories."""\n\n')
    f.write('EVERYDAY_FACTS: tuple[str, ...] = (\n')
    for s in everyday_facts:
        f.write(f'    {repr(s)},\n')
    f.write(')\n\n')
    
    f.write('NATURE_FACTS: tuple[str, ...] = (\n')
    for s in nature_facts:
        f.write(f'    {repr(s)},\n')
    f.write(')\n')

print(f"Generated {len(science_facts)} science, {len(technology_facts)} tech, {len(everyday_facts)} everyday, {len(nature_facts)} nature facts.")
