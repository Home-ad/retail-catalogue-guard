CATEGORY_EN = {
    "lait et produits laitiers": "Milk and dairy products",
    "viandes": "Meat",
    "produits de la pêche et d'aquaculture": "Fish and aquaculture products",
    "autres": "Other food products",
    "plats préparés et snacks": "Prepared meals and snacks",
    "céréales et produits de boulangerie": "Cereals and bakery products",
    "aliments diététiques et nutrition": "Dietary and nutrition products",
    "produits sucrés": "Confectionery and sweet products",
    "fruits et légumes": "Fruit and vegetables",
    "herbes et épices": "Herbs and spices",
    "soupes, sauces et condiments": "Soups, sauces and condiments",
    "noix et graines": "Nuts and seeds",
    "cacao, café et thé": "Cocoa, coffee and tea",
    "boissons non alcoolisées": "Non-alcoholic drinks",
    "aliments pour animaux domestiques": "Pet food",
    "alcool et vin": "Alcohol and wine",
    "aliments pour bébés": "Baby food",
    "oeufs et produits à base d'oeufs": "Eggs and egg products",
    "additifs alimentaires": "Food additives",
    "beurres d'origine végétale, graisses margarines et huiles": "Plant-based fats, margarines and oils",
    "aliments pour animaux d'élevage": "Animal feed",
    "escargots et grenouilles": "Snails and frogs",
    "miel et gelée royale": "Honey and royal jelly",
    "eaux": "Water",
}


def category_english(value):
    return CATEGORY_EN.get(value, "Unmapped source category")
