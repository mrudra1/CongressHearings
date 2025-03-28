''''''
def write_and_print(text, PATH):
    print(text)
    with open( PATH , 'a') as file:
        file.write('\n'+text)