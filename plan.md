1. **Define Core Exceptions (`src/core/exceptions.py`)**
   - Create domain-specific exceptions like `BachataEngineError`, `RepositoryError`, `StorageError`, and `CacheError` to gracefully handle failures without relying on generic exceptions.

2. **Implement Generic Repository Pattern (`src/core/repository.py`)**
   - Define a `ModelRepository` Protocol with standard operations: `get`, `save`, and `delete`.
   - Implement `FileSystemRepository` as a concrete class relying on generic typing for seamless integration with Pydantic domain models.

3. **Build the Caching Service & Decorator (`src/core/caching.py`)**
   - Implement a generic advanced caching decorator `repository_cache` that seamlessly stores and fetches computation results using the `ModelRepository` to isolate data logic.
   - Ensure a robust `CacheService` handles generation of unique cache keys based on method arguments and function names.

4. **Integration & Validation Tests (`tests/test_caching.py`)**
   - Write comprehensive tests to demonstrate the `FileSystemRepository` working properly with the caching layer, proving the cache mechanism is interface-driven, avoids redundant calls, and effectively leverages standard Pydantic models.

5. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
