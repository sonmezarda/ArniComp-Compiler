int foo() {
    return 5 + 3;
}

int main() {
    volatile char a = 0;
    a = foo();
}
