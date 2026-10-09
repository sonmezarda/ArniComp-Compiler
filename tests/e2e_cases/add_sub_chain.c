int main() {
    volatile char a = 7;
    volatile char b = 8;
    volatile char c = 0;

    c = a + b;
    a = c - b;
}
