import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:ecocycle_ai/core/app_state.dart';
import 'package:ecocycle_ai/screens/add_item_screen.dart';
import 'package:ecocycle_ai/screens/circular_marketplace_screen.dart';
import 'package:ecocycle_ai/screens/home_screen.dart';
import 'package:ecocycle_ai/screens/main_shell.dart';
import 'package:ecocycle_ai/screens/marketplace_browse_screen.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Home -> Circular Marketplace -> Add Item & Purchase Item -> Back -> Home navigation flow',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: HomeScreen(appState: appState),
    ));
    await tester.pumpAndSettle();

    // 1. Verify Home screen renders Circular Marketplace card
    expect(find.text('Circular Marketplace'), findsOneWidget);

    // 2. Tap Circular Marketplace card on Home
    await tester.tap(find.text('Circular Marketplace'));
    await tester.pumpAndSettle();

    // 3. Verify CircularMarketplaceScreen is pushed onto Navigator
    expect(find.byType(CircularMarketplaceScreen), findsOneWidget);
    expect(find.text('Add Item'), findsOneWidget);
    expect(find.text('Purchase Item'), findsOneWidget);

    // 4. Tap "Add Item"
    await tester.tap(find.text('Add Item'));
    await tester.pumpAndSettle();

    // 5. Verify AddItemScreen opened and shows Sell / Give Away choices
    expect(find.byType(AddItemScreen), findsOneWidget);
    expect(find.text('Sell'), findsOneWidget);
    expect(find.text('Give Away'), findsOneWidget);
    expect(find.text('Item Name'), findsOneWidget);

    // 6. Tap Back on AddItemScreen -> returns to CircularMarketplaceScreen
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded).last);
    await tester.pumpAndSettle();
    expect(find.byType(CircularMarketplaceScreen), findsOneWidget);
    expect(find.byType(AddItemScreen), findsNothing);

    // 7. Tap "Purchase Item"
    await tester.tap(find.text('Purchase Item'));
    await tester.pumpAndSettle();

    // 8. Verify MarketplaceBrowseScreen opened
    expect(find.byType(MarketplaceBrowseScreen), findsOneWidget);
    expect(find.text('Search items...'), findsOneWidget);

    // 9. Tap Back on MarketplaceBrowseScreen -> returns to CircularMarketplaceScreen
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded).last);
    await tester.pumpAndSettle();
    expect(find.byType(CircularMarketplaceScreen), findsOneWidget);
    expect(find.byType(MarketplaceBrowseScreen), findsNothing);

    // 10. Tap Back on CircularMarketplaceScreen -> returns to HomeScreen!
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded).last);
    await tester.pumpAndSettle();
    expect(find.byType(HomeScreen), findsOneWidget);
    expect(find.byType(CircularMarketplaceScreen), findsNothing);
  });

  testWidgets('MainShell Tab 2 renders CircularMarketplaceScreen and Back returns to Tab 0 Home',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);

    final appState = AppState();
    await tester.pumpWidget(MaterialApp(
      home: MainShell(appState: appState),
    ));
    await tester.pumpAndSettle();

    // Tap Marketplace tab on bottom nav (Tab 2)
    await tester.tap(find.byIcon(Icons.storefront_outlined).last);
    await tester.pumpAndSettle();

    // Verify CircularMarketplaceScreen is rendered
    expect(find.byType(CircularMarketplaceScreen), findsOneWidget);
    expect(find.text('Add Item'), findsOneWidget);
    expect(find.text('Purchase Item'), findsOneWidget);

    // Tap back arrow on CircularMarketplaceScreen when on Tab 2 -> returns to Home (Tab 0)
    await tester.tap(find.byIcon(Icons.arrow_back_ios_new_rounded).last);
    await tester.pumpAndSettle();

    // Verify Tab 0 (Home) is active
    expect(find.text('Hello, Sakshi!'), findsOneWidget);
  });
}
